import asyncio
import logging
from datetime import date, datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo

from .database import get_db_session
from .models import HrUsageMetric, QueryLog

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
METRICS_HOUR_MSK = 3


def _actor_key(user_login: str | None, user_ip: str | None) -> str | None:
    login = (user_login or "").strip()
    if login:
        return f"login:{login}"
    ip = (user_ip or "").strip()
    if ip:
        return f"ip:{ip}"
    return None


def _local_day_to_utc_range(day_local: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(day_local, dt_time.min, tzinfo=MOSCOW_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _collect_actor_days(start_day_local: date, end_day_local: date) -> dict[str, set[date]]:
    """
    Собирает активные дни пользователей за диапазон [start_day_local, end_day_local] включительно, в MSK.
    """
    start_utc, _ = _local_day_to_utc_range(start_day_local)
    _, end_utc = _local_day_to_utc_range(end_day_local + timedelta(days=1))

    actor_days: dict[str, set[date]] = {}
    with get_db_session() as db:
        rows = (
            db.query(QueryLog.user_login, QueryLog.user_ip, QueryLog.created_at)
            .filter(
                QueryLog.created_at >= start_utc,
                QueryLog.created_at < end_utc,
            )
            .all()
        )

    for row in rows:
        actor = _actor_key(row.user_login, row.user_ip)
        if not actor or row.created_at is None:
            continue
        local_day = row.created_at.astimezone(MOSCOW_TZ).date()
        if local_day < start_day_local or local_day > end_day_local:
            continue
        actor_days.setdefault(actor, set()).add(local_day)

    return actor_days


def _calc_retention(window_days: int, target_day_local: date) -> float | None:
    """
    Retention % за окно window_days:
    users with >1 уникальных активных дней / users with >=1 активный день.
    """
    window_start = target_day_local - timedelta(days=window_days - 1)
    actor_days = _collect_actor_days(window_start, target_day_local)

    total_users = len(actor_days)
    if total_users == 0:
        return None

    returned_users = sum(1 for days in actor_days.values() if len(days) > 1)
    return round((returned_users / total_users) * 100, 2)


def _calc_dau(target_day_local: date) -> int:
    actor_days = _collect_actor_days(target_day_local, target_day_local)
    return len(actor_days)


def _month_bounds_prev_month(execution_day_local: date) -> tuple[date, date]:
    current_month_start = execution_day_local.replace(day=1)
    prev_month_last_day = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_last_day.replace(day=1)
    return prev_month_start, prev_month_last_day


def _calc_mau_previous_month(execution_day_local: date) -> int:
    prev_month_start, prev_month_last_day = _month_bounds_prev_month(execution_day_local)
    actor_days = _collect_actor_days(prev_month_start, prev_month_last_day)
    return len(actor_days)


def persist_daily_metrics(execution_day_local: date) -> None:
    """
    Ежедневный расчет в 03:00 MSK. DAU/Retention считаются за предыдущий день.
    """
    target_day = execution_day_local - timedelta(days=1)
    dau = _calc_dau(target_day)
    retention_week = _calc_retention(7, target_day)
    retention_month = _calc_retention(30, target_day)
    retention_quarter = _calc_retention(90, target_day)

    with get_db_session() as db:
        metric = db.query(HrUsageMetric).filter(HrUsageMetric.metric_date == target_day).one_or_none()
        if metric is None:
            metric = HrUsageMetric(metric_date=target_day)
            db.add(metric)

        metric.dau = dau
        metric.retention_week = retention_week
        metric.retention_month = retention_month
        metric.retention_quarter = retention_quarter
        metric.calculated_at = datetime.now(timezone.utc)
        metric.source_timezone = "Europe/Moscow"

    logger.info(
        "Daily metrics saved: metric_date=%s, dau=%s, retention_week=%s, retention_month=%s, retention_quarter=%s",
        target_day,
        dau,
        retention_week,
        retention_month,
        retention_quarter,
    )


def persist_monthly_mau(execution_day_local: date) -> None:
    """
    Ежемесячный расчет MAU в 1-й день месяца в 03:00 MSK.
    Значение сохраняется в строку с metric_date=execution_day_local.
    """
    mau = _calc_mau_previous_month(execution_day_local)

    with get_db_session() as db:
        metric = db.query(HrUsageMetric).filter(HrUsageMetric.metric_date == execution_day_local).one_or_none()
        if metric is None:
            metric = HrUsageMetric(metric_date=execution_day_local)
            db.add(metric)

        metric.mau = mau
        metric.calculated_at = datetime.now(timezone.utc)
        metric.source_timezone = "Europe/Moscow"

    logger.info("Monthly MAU saved: metric_date=%s, mau=%s", execution_day_local, mau)


async def run_metrics_scheduler(poll_interval_seconds: int = 300) -> None:
    """
    Фоновый планировщик метрик.
    - Каждый день после 03:00 MSK: daily расчет за предыдущий день.
    - 1-го числа месяца после 03:00 MSK: monthly MAU расчет.
    """
    last_daily_execution_day: date | None = None
    last_monthly_execution_key: str | None = None

    logger.info("Metrics scheduler started (poll_interval_seconds=%s)", poll_interval_seconds)

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_msk = now_utc.astimezone(MOSCOW_TZ)
            execution_day = now_msk.date()

            if now_msk.hour >= METRICS_HOUR_MSK:
                if last_daily_execution_day != execution_day:
                    persist_daily_metrics(execution_day)
                    last_daily_execution_day = execution_day

                monthly_key = execution_day.strftime("%Y-%m")
                if execution_day.day == 1 and last_monthly_execution_key != monthly_key:
                    persist_monthly_mau(execution_day)
                    last_monthly_execution_key = monthly_key

            await asyncio.sleep(poll_interval_seconds)
        except asyncio.CancelledError:
            logger.info("Metrics scheduler stopped")
            raise
        except Exception as exc:
            logger.exception("Metrics scheduler iteration failed: %s", exc)
            await asyncio.sleep(min(poll_interval_seconds, 60))
