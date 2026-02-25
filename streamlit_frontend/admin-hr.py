import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


# Настройка страницы
st.set_page_config(page_title="HR консультант", layout="wide")

# Базовый стиль, ближе к референсному скриншоту
st.markdown(
    """
<style>
h1 {
    font-family: "Times New Roman", Times, serif !important;
    font-size: 56px !important;
    font-weight: 700 !important;
}
h2, h3 {
    font-family: "Times New Roman", Times, serif !important;
}
.metric-label {
    color: #444;
    font-size: 14px;
}
.metric-value {
    font-size: 48px;
    font-family: "Times New Roman", Times, serif;
    line-height: 1.05;
}
.metric-good {
    color: #2ca02c;
}
</style>
""",
    unsafe_allow_html=True,
)


def get_api_base_url() -> str:
    env_url = os.environ.get("API_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    try:
        secrets_url = st.secrets.get("API_BASE_URL")
        if secrets_url:
            return str(secrets_url).rstrip("/")
    except Exception:
        pass

    return "http://localhost:8000"


def get_api_base_url_candidates() -> list:
    """Формирует список кандидатов API URL в порядке приоритета."""
    candidates = []

    configured_url = get_api_base_url().rstrip("/")
    if configured_url:
        candidates.append(configured_url)

    for fallback in ("http://localhost:8000", "http://127.0.0.1:8000"):
        if fallback not in candidates:
            candidates.append(fallback)

    return candidates


@st.cache_data(ttl=30)
def fetch_admin_report(
    start_date: str,
    end_date: str,
    score_type: str,
    context_found_only: bool,
    limit: int,
):
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "score_type": score_type,
        "context_found_only": context_found_only,
        "limit": limit,
    }

    last_error = None
    for base_url in get_api_base_url_candidates():
        endpoint = f"{base_url}/api/admin/hr-report"
        try:
            response = requests.get(endpoint, params=params, timeout=8)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise requests.RequestException("Не удалось определить рабочий URL backend")


# Боковая панель с фильтрами
with st.sidebar:
    st.header("Настройки фильтров")

    # Неделя в фильтре начинается с понедельника
    today = datetime.utcnow().date()
    default_start = today - timedelta(days=today.weekday())  # Monday
    default_end = today

    # Даты
    st.subheader("Дата начала")
    date_start = st.date_input(
        "Дата начала",
        value=default_start,
        key="start_date",
        format="DD.MM.YYYY",
        label_visibility="collapsed",
    )

    st.subheader("Дата окончания")
    date_end = st.date_input(
        "Дата окончания",
        value=default_end,
        key="end_date",
        format="DD.MM.YYYY",
        label_visibility="collapsed",
    )

    # Тип оценки
    st.subheader("Тип оценки")
    score_type_ui = st.radio(
        "Тип оценки",
        options=["Все", "Like", "Dislike"],
        index=0,
        label_visibility="collapsed",
    )

    # Контекст найден
    st.subheader("Контекст найден")
    filter_context = st.checkbox("Контекст найден", value=True)

    # Максимальное количество строк
    max_rows = st.slider(
        "Максимальное количество строк в таблице",
        min_value=5,
        max_value=100,
        value=10,
    )

    # Кнопка оставлена для UX, но фильтры применяются автоматически при изменении
    # if st.button("Применить фильтр"):
    #     st.cache_data.clear()

    # st.markdown("---")

score_type_map = {
    "Все": "all",
    "Like": "like",
    "Dislike": "dislike",
}

def build_questions_dataframe(rows: list) -> pd.DataFrame:
    table_data = []
    for row in rows:
        row_date_raw = row.get("date", "")
        row_date = ""
        row_time = ""
        if row_date_raw:
            parsed_dt = pd.to_datetime(row_date_raw, utc=True).tz_convert(None)
            row_date = parsed_dt.strftime("%Y-%m-%d")
            row_time = parsed_dt.strftime("%H:%M:%S")

        table_data.append(
            {
                "ID": row.get("id"),
                "Дата": row_date,
                "Время": row_time,
                "Вопрос": (row.get("question") or "").strip() or "—",
                "Ответ": (row.get("answer") or "").strip() or "—",
                "Оценка": row.get("operation", ""),
                "Контекст": row.get("content", ""),
                "Статус": row.get("status", ""),
            }
        )
    return pd.DataFrame(table_data)


def build_analytics_dataframe(report_data: dict) -> pd.DataFrame:
    """
    Строит ряд метрик для вкладки аналитики.
    1) Если backend отдает сохраненные срезы метрик (metrics_history), используем их.
    2) Иначе строим fallback из daily_stats + текущих DAO/MAO.
    """
    raw_history = report_data.get("metrics_history") or report_data.get("analytics_history") or []
    if raw_history:
        normalized = []
        for item in raw_history:
            metric_date = item.get("date") or item.get("day")
            if not metric_date:
                continue
            retention_value = item.get("retention_rate")
            if retention_value is None:
                retention_value = item.get("retension_rate")
            normalized.append(
                {
                    "Дата": metric_date,
                    "DAU": item.get("dau", item.get("dao")),
                    "MAU": item.get("mau", item.get("mao")),
                    "Retention 7d, %": item.get("retention_week", retention_value),
                    "Retention 30d, %": item.get("retention_month"),
                    "Retention 90d, %": item.get("retention_quarter"),
                }
            )
        if normalized:
            df = pd.DataFrame(normalized)
            df["Дата"] = pd.to_datetime(df["Дата"], errors="coerce")
            return df.sort_values("Дата").reset_index(drop=True)

    daily_stats = report_data.get("daily_stats", [])
    if not daily_stats:
        return pd.DataFrame(columns=["Дата", "DAU", "MAU", "Retention 7d, %", "Retention 30d, %", "Retention 90d, %"])

    df = pd.DataFrame(daily_stats).rename(columns={"day": "Дата", "count": "DAU"})
    df["Дата"] = pd.to_datetime(df["Дата"], errors="coerce")
    df = df.sort_values("Дата").reset_index(drop=True)

    df["Retention 7d, %"] = pd.NA
    df["Retention 30d, %"] = pd.NA
    df["Retention 90d, %"] = pd.NA
    df["MAU"] = pd.NA
    if not df.empty:
        current_month_start = pd.Timestamp(datetime(date_end.year, date_end.month, 1).date())
        df.loc[df["Дата"] == current_month_start, "MAU"] = report_data.get("mao", 0)

    return df


if date_end < date_start:
    st.error("Дата окончания не может быть меньше даты начала")
    st.stop()

try:
    report = fetch_admin_report(
        start_date=date_start.isoformat(),
        end_date=date_end.isoformat(),
        score_type=score_type_map[score_type_ui],
        context_found_only=filter_context,
        limit=max_rows,
    )
except requests.RequestException as exc:
    st.error(f"Не удалось получить данные из backend: {exc}")
    st.stop()

tab_questions, tab_analytics = st.tabs(["Вопросы и ответы", "Аналитика"])

with tab_questions:
    st.title("Список вопросов и ответов")
    st.markdown(f"**Отчет за период с {date_start.strftime('%d.%m.%Y')} по {date_end.strftime('%d.%m.%Y')}**")
    st.markdown("---")

    st.subheader("Детальные результаты")
    rows = report.get("rows", [])
    if rows:
        df_rows = build_questions_dataframe(rows)
        st.dataframe(df_rows, use_container_width=True, hide_index=True)
    else:
        st.info("По выбранным настройкам данных не найдено.")

with tab_analytics:
    st.title("Аналитика")
    st.markdown(f"**Интервал анализа: {date_start.strftime('%d.%m.%Y')} - {date_end.strftime('%d.%m.%Y')}**")
    st.caption(
        "DAU и Retention Rate считаются ежедневно в 03:00 (Europe/Moscow), "
        "MAU рассчитывается 1-го числа месяца в 03:00 (Europe/Moscow)."
    )

    dau = report.get("dao", 0)
    mau = report.get("mao", 0)

    analytics_df = build_analytics_dataframe(report)
    retention_7d_latest = None
    retention_30d_latest = None
    retention_90d_latest = None
    if not analytics_df.empty:
        retention_7d_series = analytics_df["Retention 7d, %"].dropna()
        retention_30d_series = analytics_df["Retention 30d, %"].dropna()
        retention_90d_series = analytics_df["Retention 90d, %"].dropna()
        if not retention_7d_series.empty:
            retention_7d_latest = float(retention_7d_series.iloc[-1])
        if not retention_30d_series.empty:
            retention_30d_latest = float(retention_30d_series.iloc[-1])
        if not retention_90d_series.empty:
            retention_90d_latest = float(retention_90d_series.iloc[-1])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("DAU", int(dau) if pd.notna(dau) else 0)
    with col2:
        st.metric("MAU", int(mau) if pd.notna(mau) else 0)
    with col3:
        if retention_7d_latest is not None:
            st.metric("Retention 7d", f"{retention_7d_latest:.2f}%")
        else:
            st.metric("Retention 7d", "—")
    with col4:
        if retention_30d_latest is not None:
            st.metric("Retention 30d", f"{retention_30d_latest:.2f}%")
        else:
            st.metric("Retention 30d", "—")
    with col5:
        if retention_90d_latest is not None:
            st.metric("Retention 90d", f"{retention_90d_latest:.2f}%")
        else:
            st.metric("Retention 90d", "—")

    st.markdown("---")
    st.subheader("График DAU по дням.")
    if analytics_df.empty:
        st.info("Нет данных для построения графиков.")
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=analytics_df["Дата"],
                y=analytics_df["DAU"],
                name="DAU",
                marker_color="#1f77b4",
                opacity=0.85,
            )
        )

        fig.update_layout(
            height=450,
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", y=1.12, x=0),
        )
        fig.update_xaxes(title_text="Дата", gridcolor="lightgray")
        fig.update_yaxes(title_text="Пользователи", gridcolor="lightgray")
        st.plotly_chart(fig, use_container_width=True)
# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>HR консультант © 2026</div>", unsafe_allow_html=True)
