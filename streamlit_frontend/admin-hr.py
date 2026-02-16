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

    default_end = datetime.utcnow().date()
    default_start = default_end - timedelta(days=1)

    # Даты
    st.subheader("Дата начала")
    date_start = st.date_input(
        "Дата начала",
        value=default_start,
        key="start_date",
        label_visibility="collapsed",
    )

    st.subheader("Дата окончания")
    date_end = st.date_input(
        "Дата окончания",
        value=default_end,
        key="end_date",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Тип оценки
    st.subheader("Тип оценки")
    score_type_ui = st.radio(
        "Тип оценки",
        options=["Все", "Только Like", "Только Dislike"],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Контекст найден
    st.subheader("Контекст найден")
    filter_context = st.checkbox("Контекст найден", value=True)

    st.markdown("---")

    # Максимальное количество строк
    max_rows = st.slider(
        "Максимальное количество строк в таблице",
        min_value=5,
        max_value=100,
        value=10,
    )

    st.markdown("---")

    # Кнопка оставлена для UX, но фильтры применяются автоматически при изменении
    if st.button("Применить фильтр"):
        st.cache_data.clear()

    st.markdown("---")
    st.subheader("Отображение данных")


score_type_map = {
    "Все": "all",
    "Только Like": "like",
    "Только Dislike": "dislike",
}

# Основной контент
st.title("Результаты работы приложения")
st.markdown(f"**Отчет за период с {date_start.strftime('%d.%m.%Y')} по {date_end.strftime('%d.%m.%Y')}**")
st.markdown("---")

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

# Расчет метрик из API
total_records = report.get("total_records", 0)
like_count = report.get("like_count", 0)
dislike_count = report.get("dislike_count", 0)
context_found = report.get("context_found", 0)
dao = report.get("dao", 0)
mao = report.get("mao", 0)

# Отображение метрик в пять колонок
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="metric-label">Всего записей</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{total_records}</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-good">↑ +12.3% vs вчера</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-label">Like / Dislike</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{like_count} / {dislike_count}</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-good">↑ 100.0% позитивных</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-label">Контекст найден</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{context_found}</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-good">↑ 100.0% успешно</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-label">DAO</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{dao}</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-good">уникальных пользователей</div>', unsafe_allow_html=True)

with col5:
    st.markdown('<div class="metric-label">MAO</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{mao}</div>', unsafe_allow_html=True)
    st.markdown('<div class="metric-good">уникальных пользователей</div>', unsafe_allow_html=True)

st.markdown("---")

# Детальные результаты
st.subheader("Детальные результаты")

rows = report.get("rows", [])
if rows:
    st.markdown("**Раскрытие строк (вопрос/ответ)**")
    for row in rows:
        row_id = row.get("id")
        row_date_raw = row.get("date", "")
        row_date = ""
        row_time = ""
        if row_date_raw:
            parsed_dt = pd.to_datetime(row_date_raw, utc=True).tz_convert(None)
            row_date = parsed_dt.strftime("%Y-%m-%d")
            row_time = parsed_dt.strftime("%H:%M:%S")
        row_operation = row.get("operation", "")
        row_content = row.get("content", "")
        row_status = row.get("status", "")
        row_question = (row.get("question") or "").strip()
        row_answer = (row.get("answer") or "").strip()

        title = (
            f"id: {row_id} | дата={row_date} | время: {row_time} | "
            f"Оценка: {row_operation} | Контент: {row_content} | статус выполнения: {row_status}"
        )
        with st.expander(title):
            st.markdown("**Вопрос:**")
            st.write(row_question or "—")
            st.markdown("**Ответ:**")
            st.write(row_answer or "—")
else:
    st.warning("Нет данных для отображения")

st.markdown("---")

# График оценок
st.subheader("График оценок")

daily_stats = report.get("daily_stats", [])
if daily_stats:
    days = [item["day"] for item in daily_stats]
    counts = [item["count"] for item in daily_stats]

    fig = go.Figure(
        data=[
            go.Bar(
                x=days,
                y=counts,
                marker_color="#1f77b4",
                hovertemplate="Дата: %{x}<br>Количество: %{y}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Количество оценок",
        showlegend=False,
        height=400,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
    )

    fig.update_xaxes(gridcolor="lightgray")
    fig.update_yaxes(gridcolor="lightgray")

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Нет данных для построения графика")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>HR консультант © 2026</div>", unsafe_allow_html=True)
