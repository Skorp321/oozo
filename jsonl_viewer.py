import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

# Настройка страницы
st.set_page_config(
    page_title="JSONL Viewer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_jsonl_file(file_path):
    """Загружает JSONL файл и возвращает список записей"""
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        record['_line_number'] = line_num
                        records.append(record)
                    except json.JSONDecodeError as e:
                        st.error(f"Ошибка парсинга JSON в строке {line_num}: {e}")
                        continue
        return records
    except FileNotFoundError:
        st.error(f"Файл не найден: {file_path}")
        return []
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return []

def format_timestamp(timestamp_str):
    """Форматирует временную метку для удобного отображения"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except:
        return timestamp_str

def display_record(record, index, default_expanded=False):
    """Отображает одну запись в удобном формате"""
    # Создаем заголовок с основной информацией для expander'а
    timestamp = format_timestamp(record.get('timestamp', ''))
    status_color = "🟢" if record.get('status') == 'success' else "🔴"
    question = record.get('request', {}).get('question', '')[:50]
    if len(question) > 50:
        question += "..."
    
    expander_title = f"📋 Запись #{index + 1} | {timestamp} | {status_color} {record.get('status', '')} | {question}"
    
    with st.expander(expander_title, expanded=default_expanded):
        # Основная информация в колонках
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 📊 Метаданные")
            
            # Временная метка
            if 'timestamp' in record:
                st.write(f"**Время:** {format_timestamp(record['timestamp'])}")
            
            # Тип записи
            if 'type' in record:
                st.write(f"**Тип:** {record['type']}")
            
            # Статус
            if 'status' in record:
                status_color = "🟢" if record['status'] == 'success' else "🔴"
                st.write(f"**Статус:** {status_color} {record['status']}")
            
            # Время обработки
            if 'processing_time_seconds' in record:
                st.write(f"**Время обработки:** {record['processing_time_seconds']:.2f} сек")
            
            # Количество источников
            if 'response' in record and 'sources_count' in record['response']:
                st.write(f"**Источников:** {record['response']['sources_count']}")
            
            # Ошибка
            if 'error' in record and record['error']:
                st.error(f"**Ошибка:** {record['error']}")
        
        with col2:
            st.markdown("#### 💬 Содержимое")
            
            # Запрос
            if 'request' in record:
                st.markdown("**Запрос:**")
                if 'question' in record['request']:
                    st.info(record['request']['question'])
                else:
                    st.json(record['request'])
            
            # Ответ
            if 'response' in record:
                st.markdown("**Ответ:**")
                if 'answer' in record['response']:
                    st.markdown(record['response']['answer'])
                else:
                    st.json(record['response'])
        
        # Источники (если есть)
        if 'response' in record and 'sources_payload' in record['response']:
            st.markdown("#### 📚 Источники")
            sources = record['response']['sources_payload']
            
            for i, source in enumerate(sources):
                st.markdown(f"**Источник {i+1}: {source.get('title', 'Без названия')}** (релевантность: {source.get('score', 0):.2f})")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**Содержание:**")
                    st.text(source.get('content', 'Нет содержимого'))
                
                with col2:
                    st.markdown("**Метаданные:**")
                    metadata = source.get('metadata', {})
                    if metadata:
                        st.write(f"**Файл:** {metadata.get('file_path', 'N/A')}")
                        st.write(f"**Размер:** {metadata.get('file_size', 'N/A')} байт")
                        st.write(f"**Чанк:** {metadata.get('chunk_id', 'N/A')} из {metadata.get('total_chunks', 'N/A')}")
                        st.write(f"**Источник:** {metadata.get('source', 'N/A')}")
                
                if i < len(sources) - 1:  # Добавляем разделитель между источниками
                    st.markdown("---")

def main():
    st.title("📄 JSONL Viewer")
    st.markdown("Просмотрщик JSONL файлов с удобным интерфейсом")
    
    # Боковая панель
    st.sidebar.header("⚙️ Настройки")
    
    # Выбор файла
    file_path = st.sidebar.text_input(
        "Путь к JSONL файлу:",
        value="backend/data/logs/qa_logs.jsonl",
        help="Введите полный путь к JSONL файлу"
    )
    
    # Кнопка загрузки
    if st.sidebar.button("📂 Загрузить файл", type="primary"):
        if file_path and os.path.exists(file_path):
            st.session_state.file_path = file_path
            st.session_state.records = load_jsonl_file(file_path)
            st.success(f"Файл загружен: {len(st.session_state.records)} записей")
        else:
            st.error("Файл не найден. Проверьте путь.")
    
    # Фильтры
    st.sidebar.header("🔍 Фильтры")
    
    if 'records' in st.session_state and st.session_state.records:
        # Фильтр по дате
        st.sidebar.subheader("📅 Фильтр по дате")
        
        # Получаем минимальную и максимальную даты из записей
        timestamps = []
        for record in st.session_state.records:
            if 'timestamp' in record:
                try:
                    dt = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(dt)
                except:
                    continue
        
        if timestamps:
            min_date = min(timestamps).date()
            max_date = max(timestamps).date()
            
            start_date = st.sidebar.date_input(
                "Начальная дата:",
                value=min_date,
                min_value=min_date,
                max_value=max_date
            )
            
            end_date = st.sidebar.date_input(
                "Конечная дата:",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        else:
            start_date = None
            end_date = None
        

        
        # Применение фильтров
        filtered_records = st.session_state.records.copy()
        
        # Фильтр по дате
        if start_date and end_date:
            filtered_records = [r for r in filtered_records 
                              if 'timestamp' in r and 
                              start_date <= datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')).date() <= end_date]
        
        st.session_state.filtered_records = filtered_records

    # Главная страница
    if 'filtered_records' in st.session_state and st.session_state.filtered_records:
        records = st.session_state.filtered_records
        
        # Статистика
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего записей", len(records))
        with col2:
            success_count = len([r for r in records if r.get('status') == 'success'])
            st.metric("Успешных", success_count)
        with col3:
            avg_time = sum(r.get('processing_time_seconds', 0) for r in records) / len(records)
            st.metric("Среднее время", f"{avg_time:.2f} сек")
        with col4:
            total_sources = sum(r.get('response', {}).get('sources_count', 0) for r in records)
            st.metric("Всего источников", total_sources)
        
        st.divider()
        
        # Отображение записей
        st.subheader(f"📋 Записи ({len(records)} из {len(st.session_state.records)})")
        
        # Опции отображения
        col1, col2 = st.columns([2, 1])
        
        with col1:
            display_mode = st.radio(
                "Режим отображения:",
                ["Развернутый", "Компактный", "Таблица"],
                horizontal=True
            )
        
        with col2:
            if display_mode == "Развернутый":
                default_expanded = st.checkbox("Развернуть записи по умолчанию", value=False)
            else:
                default_expanded = False
        
        if display_mode == "Таблица":
            # Создание таблицы
            table_data = []
            for record in records:
                row = {
                    '№': record.get('_line_number', 'N/A'),
                    'Время': format_timestamp(record.get('timestamp', '')),
                    'Тип': record.get('type', ''),
                    'Статус': record.get('status', ''),
                    'Время обработки (сек)': f"{record.get('processing_time_seconds', 0):.2f}",
                    'Вопрос': record.get('request', {}).get('question', '')[:100] + '...' if len(record.get('request', {}).get('question', '')) > 100 else record.get('request', {}).get('question', ''),
                    'Источников': record.get('response', {}).get('sources_count', 0),
                    'Есть детали источников': 'Да' if record.get('response', {}).get('sources_payload') else 'Нет'
                }
                table_data.append(row)
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
            
        else:
            # Развернутый или компактный режим
            for i, record in enumerate(records):
                if display_mode == "Компактный":
                    # Компактный режим - показываем только основную информацию
                    st.markdown(f"---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        st.write(f"**#{i + 1}**")
                        st.write(f"**{format_timestamp(record.get('timestamp', ''))}**")
                        status_color = "🟢" if record.get('status') == 'success' else "🔴"
                        st.write(f"{status_color} {record.get('status', '')}")
                    
                    with col2:
                        question = record.get('request', {}).get('question', '')
                        st.write(f"**Вопрос:** {question}")
                        answer = record.get('response', {}).get('answer', '')
                        st.write(f"**Ответ:** {answer}")
                    
                    with col3:
                        st.write(f"**{record.get('processing_time_seconds', 0):.2f} сек**")
                        st.write(f"**{record.get('response', {}).get('sources_count', 0)} источников**")
                        if record.get('response', {}).get('sources_payload'):
                            st.write("📚 **Детали источников**")
                else:
                    # Развернутый режим
                    display_record(record, i, default_expanded)
    
    elif 'records' in st.session_state and not st.session_state.records:
        st.warning("Файл пуст или не содержит валидных JSON записей")
    
    else:
        st.info("👈 Выберите файл в боковой панели для начала работы")

if __name__ == "__main__":
    main()
