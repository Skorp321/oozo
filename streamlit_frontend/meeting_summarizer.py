import streamlit as st
import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import tempfile
import io
from datetime import datetime

# Конфигурация страницы
st.set_page_config(
    page_title="Суммаризация итогов встречи",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
        font-size: 2.5rem;
    }
    
    .description-box {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
        border-left: 4px solid #007bff;
    }
    
    .upload-section {
        background-color: #e3f2fd;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .summary-container {
        background-color: #f5f5f5;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #4caf50;
    }
    
    .streaming-text {
        font-family: 'Courier New', monospace;
        background-color: white;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #dee2e6;
        min-height: 200px;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .download-button {
        background-color: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        margin-top: 1rem;
    }
    
    .download-button:hover {
        background-color: #218838;
    }
    
    .stButton > button {
        border-radius: 10px;
        background-color: #007bff;
        color: white;
        border: none;
        height: 44px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background-color: #0056b3;
    }
    
    .file-uploader {
        border: 2px dashed #007bff;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f8f9fa;
    }
    
    /* Стили для радиокнопок */
    .stRadio > div {
        margin-bottom: 1rem;
    }
    
    .stRadio > div > label {
        font-weight: 500;
        color: #333;
    }
    
    /* Стили для информационных блоков */
    .stAlert {
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Инициализация состояния сессии"""
    if "summary_text" not in st.session_state:
        st.session_state.summary_text = ""
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    if "file_uploaded" not in st.session_state:
        st.session_state.file_uploaded = False
    if "uploaded_file_content" not in st.session_state:
        st.session_state.uploaded_file_content = ""
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = "meeting_summary"

def read_file_content(uploaded_file):
    """Чтение содержимого загруженного файла"""
    try:
        # Определяем тип файла по расширению
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension in ['txt', 'md']:
            # Текстовые файлы
            content = uploaded_file.read().decode('utf-8')
        elif file_extension in ['docx', 'doc']:
            # Word документы
            import docx
            doc = docx.Document(uploaded_file)
            content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        elif file_extension == 'pdf':
            # PDF файлы
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        else:
            # Попытка прочитать как текст
            content = uploaded_file.read().decode('utf-8', errors='ignore')
        
        return content.strip()
    except Exception as e:
        st.error(f"Ошибка при чтении файла: {str(e)}")
        return None

def get_system_prompts():
    """Получение доступных системных промптов"""
    prompts = {
        "meeting_summary": {
            "name": "📝 Сводка встречи",
            "description": "Структурированная сводка с темами, решениями и задачами",
            "prompt": """Ты - профессиональный помощник по суммаризации итогов встреч. 
    Твоя задача - создать четкую, структурированную и информативную сводку встречи в формате Markdown.
    
    Структура сводки должна включать:
    1. **Основные темы обсуждения** - ключевые вопросы и темы
    2. **Принятые решения** - конкретные решения и их детали
    3. **Поручения и задачи** - кто и что должен сделать
    4. **Сроки** - важные даты и дедлайны
    5. **Следующие шаги** - план дальнейших действий
    
    Используй профессиональный, но понятный язык. Выделяй важную информацию жирным шрифтом.
    Если в тексте нет четкой структуры встречи, создай логичную сводку на основе имеющейся информации.
    
    ВАЖНО: 
    - Отвечай только в формате Markdown
    - Не используй JSON или другие форматы
    - Используй правильные заголовки Markdown (# для главного заголовка, ## для подзаголовков)
    - Не добавляй лишние звездочки вокруг заголовков"""
        },
        "action_items": {
            "name": "✅ Пункты действий",
            "description": "Фокус на задачах, поручениях и сроках",
            "prompt": """Ты - помощник по извлечению пунктов действий из встреч.
    Твоя задача - выделить все задачи, поручения и действия, которые нужно выполнить в формате Markdown.
    
    Структура должна включать:
    1. **Поручения** - кто и что должен сделать
    2. **Сроки выполнения** - даты и дедлайны
    3. **Приоритеты** - важность задач
    4. **Зависимости** - что нужно сделать перед чем
    5. **Ответственные** - кто отвечает за выполнение
    
    Используй четкий формат: "**Кто:** Что сделать - **Срок:** дата - **Приоритет:** высокий/средний/низкий"
    Выделяй критически важные задачи.
    
    ВАЖНО: 
    - Отвечай только в формате Markdown
    - Не используй JSON или другие форматы
    - Используй правильные заголовки Markdown (# для главного заголовка, ## для подзаголовков)
    - Не добавляй лишние звездочки вокруг заголовков"""
        },
        "key_decisions": {
            "name": "🎯 Ключевые решения",
            "description": "Анализ принятых решений и их обоснование",
            "prompt": """Ты - аналитик по анализу решений, принятых на встрече.
    Твоя задача - проанализировать и структурировать все принятые решения в формате Markdown.
    
    Структура должна включать:
    1. **Принятые решения** - что было решено
    2. **Обоснование** - почему принято такое решение
    3. **Альтернативы** - какие варианты рассматривались
    4. **Последствия** - что изменится после реализации
    5. **Риски** - возможные проблемы и их митигация
    
    Используй аналитический подход. Выделяй стратегические решения.
    
    ВАЖНО: 
    - Отвечай только в формате Markdown
    - Не используй JSON или другие форматы
    - Используй правильные заголовки Markdown (# для главного заголовка, ## для подзаголовков)
    - Не добавляй лишние звездочки вокруг заголовков"""
        },
        "minutes": {
            "name": "📋 Протокол встречи",
            "description": "Подробный протокол с хронологией обсуждения",
            "prompt": """Ты - секретарь, составляющий протокол встречи.
    Твоя задача - создать подробный протокол с хронологией обсуждения в формате Markdown.
    
    Структура должна включать:
    1. **Участники** - кто присутствовал на встрече
    2. **Повестка дня** - что планировалось обсудить
    3. **Ход обсуждения** - как проходила встреча
    4. **Выступления** - ключевые высказывания участников
    5. **Результаты** - итоги по каждому пункту повестки
    
    Используй формальный стиль протокола. Сохраняй хронологию.
    
    ВАЖНО: 
    - Отвечай только в формате Markdown
    - Не используй JSON или другие форматы
    - Используй правильные заголовки Markdown (# для главного заголовка, ## для подзаголовков)
    - Не добавляй лишние звездочки вокруг заголовков"""
        }
    }
    return prompts

def create_summary_prompt(content, prompt_type="meeting_summary"):
    """Создание промпта для суммаризации"""
    prompts = get_system_prompts()
    
    if prompt_type not in prompts:
        prompt_type = "meeting_summary"
    
    system_prompt = prompts[prompt_type]["prompt"]
    
    user_prompt = f"""Пожалуйста, создай {prompts[prompt_type]['name'].lower()} для следующей встречи:

{content}

Создай структурированный результат в формате Markdown, используя указанную структуру. 

ВАЖНО: 
- Отвечай только в формате Markdown
- Не используй JSON или другие форматы
- Используй правильные заголовки Markdown (# для главного заголовка, ## для подзаголовков)
- Не добавляй лишние звездочки вокруг заголовков
- Структурируй текст с помощью заголовков и списков"""
    
    return system_prompt, user_prompt

def stream_summary(llm, system_prompt, user_prompt):
    """Потоковая генерация сводки"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Создаем контейнер для отображения текста
    text_container = st.empty()
    full_response = ""
    
    # Генерируем ответ потоково
    for chunk in llm.stream(messages):
        if chunk.content:
            full_response += chunk.content
            if ('<think>' in full_response) and ('</think>' not in full_response):
                continue
            # Отображаем текст с форматированием markdown
            display_text = full_response.split('</think>')[-1] if '</think>' in full_response else full_response
            # Очищаем текст от лишних символов форматирования
            display_text = clean_markdown_text(display_text)
            text_container.markdown(display_text + "▋")
    
    # Очищаем курсор в конце
    final_text = full_response.split('</think>')[-1] if '</think>' in full_response else full_response
    final_text = clean_markdown_text(final_text)
    text_container.markdown(final_text)
    
    return final_text

def clean_markdown_text(text):
    """Очистка текста от лишних символов форматирования"""
    if not text:
        return text
    
    # Убираем лишние звездочки в начале строк
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        
        # Убираем лишние звездочки в начале заголовков
        if stripped_line.startswith('**#') and stripped_line.endswith('**'):
            # Это заголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**##') and stripped_line.endswith('**'):
            # Это подзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**###') and stripped_line.endswith('**'):
            # Это подподзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**####') and stripped_line.endswith('**'):
            # Это подподподзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**####') and stripped_line.endswith('**'):
            # Это подподподподзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**#####') and stripped_line.endswith('**'):
            # Это подподподподподзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        elif stripped_line.startswith('**######') and stripped_line.endswith('**'):
            # Это подподподподподподзаголовок с лишними звездочками
            cleaned_line = stripped_line[2:-2]  # Убираем ** в начале и конце
        else:
            cleaned_line = line
        
        cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def download_summary_as_txt(summary_text, prompt_type="meeting_summary"):
    """Создание файла для скачивания"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Получаем название типа анализа
    prompts = get_system_prompts()
    type_name = prompts.get(prompt_type, prompts["meeting_summary"])["name"]
    
    # Создаем имя файла на основе типа анализа
    filename = f"{type_name.replace(' ', '_').replace('📝', '').replace('✅', '').replace('🎯', '').replace('📋', '').strip()}_{timestamp}.txt"
    
    # Создаем временный файл
    buffer = io.StringIO()
    buffer.write(f"{type_name.upper()}\n")
    buffer.write("=" * 50 + "\n\n")
    buffer.write(summary_text)
    buffer.write(f"\n\nСоздано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    return buffer.getvalue(), filename

def main():
    # Инициализация состояния
    initialize_session_state()
    
    # Заголовок (динамический в зависимости от состояния)
    if st.session_state.is_processing:
        prompts = get_system_prompts()
        selected_type_name = prompts[st.session_state.selected_prompt]["name"]
        st.markdown(f'<h1 class="main-header">🔄 Создание {selected_type_name.lower()}</h1>', unsafe_allow_html=True)
    elif st.session_state.summary_text:
        st.markdown('<h1 class="main-header">📝 Сервис суммаризации итогов встречи</h1>', unsafe_allow_html=True)
    else:
        st.markdown('<h1 class="main-header">📝 Сервис суммаризации итогов встречи</h1>', unsafe_allow_html=True)
    
    # Описание сервиса (показывается только когда не идет обработка и нет результата)
    if not st.session_state.is_processing and not st.session_state.summary_text:
        st.markdown("""
        <div class="description-box">
            <h2>О сервисе</h2>
            <p>Этот сервис поможет вам быстро и эффективно создать структурированную сводку любой встречи. 
            Просто загрузите документ с текстом встречи, и наш ИИ создаст подробную сводку, включающую:</p>
            <ul>
                <li>Основные темы обсуждения</li>
                <li>Принятые решения</li>
                <li>Поручения и задачи</li>
                <li>Сроки и дедлайны</li>
                <li>Следующие шаги</li>
            </ul>
            <p><strong>Поддерживаемые форматы:</strong> TXT, DOCX, PDF, MD</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Боковая панель для загрузки файла
    with st.sidebar:
        st.markdown("### 📁 Загрузка файла")
        st.markdown("Загрузите документ с текстом встречи для создания сводки")
        
        uploaded_file = st.file_uploader(
            "Выберите файл",
            type=['txt', 'docx', 'pdf', 'md'],
            help="Поддерживаются файлы TXT, DOCX, PDF, MD"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ Файл загружен: {uploaded_file.name}")
            st.session_state.file_uploaded = True
            
            # Читаем содержимое файла
            if not st.session_state.uploaded_file_content:
                with st.spinner("Читаю содержимое файла..."):
                    content = read_file_content(uploaded_file)
                    if content:
                        st.session_state.uploaded_file_content = content
                        st.info(f"📄 Прочитано {len(content)} символов")
                    else:
                        st.error("Не удалось прочитать содержимое файла")
        
        # Выбор типа промпта
        st.markdown("### 🎯 Тип анализа")
        st.markdown("Выберите тип анализа для создания результата")
        
        prompts = get_system_prompts()
        prompt_options = {prompts[key]["name"]: key for key in prompts.keys()}
        
        selected_prompt_name = st.radio(
            "Выберите тип анализа:",
            options=list(prompt_options.keys()),
            index=list(prompt_options.keys()).index(prompts[st.session_state.selected_prompt]["name"]),
            help="Разные типы анализа создают различные форматы результатов"
        )
        
        # Обновляем выбранный промпт
        st.session_state.selected_prompt = prompt_options[selected_prompt_name]
        
        # Показываем описание выбранного типа
        selected_prompt_info = prompts[st.session_state.selected_prompt]
        st.info(f"**{selected_prompt_info['name']}**\n{selected_prompt_info['description']}")
        
        # Кнопка запуска обработки
        if st.session_state.file_uploaded and st.session_state.uploaded_file_content:
            if st.button("🚀 Запустить анализ", use_container_width=True):
                st.session_state.is_processing = True
                st.session_state.summary_text = ""
                st.rerun()
    
    # Основная область
    if st.session_state.is_processing and st.session_state.uploaded_file_content:
        # Показываем только заголовок и процесс обработки
        st.markdown("### 🔄 Обработка документа")
        
        # Проверяем наличие API ключа
        openai_api_key = st.secrets.get("OPENAI_API_KEY")
        if not openai_api_key:
            st.error("❌ Не найден API ключ OpenAI. Добавьте OPENAI_API_KEY в секреты Streamlit.")
            st.session_state.is_processing = False
            return
        
        try:
            # Инициализируем LLM
            llm = ChatOpenAI(
                openai_api_base="https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1",
                model="library/qwen3:32b",
                temperature=0.3,
                streaming=True,
                openai_api_key='EMPTY'
            )
            
            # Создаем промпт с выбранным типом
            system_prompt, user_prompt = create_summary_prompt(
                st.session_state.uploaded_file_content, 
                st.session_state.selected_prompt
            )
            
            # Получаем название выбранного типа анализа
            prompts = get_system_prompts()
            selected_type_name = prompts[st.session_state.selected_prompt]["name"]
            
            # Генерируем результат
            with st.spinner(f"Создаю {selected_type_name.lower()}..."):
                summary = stream_summary(llm, system_prompt, user_prompt)
                st.session_state.summary_text = summary
            
            st.session_state.is_processing = False
            st.success(f"✅ {selected_type_name} создан успешно!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Ошибка при создании результата: {str(e)}")
            st.session_state.is_processing = False
    
    # Отображение результата
    if st.session_state.summary_text and not st.session_state.is_processing:
        # Получаем название выбранного типа анализа
        prompts = get_system_prompts()
        selected_type_name = prompts[st.session_state.selected_prompt]["name"]
        
        st.markdown(f"### 📋 Результат анализа: {selected_type_name}")
        
        # Отображаем результат
        st.markdown(st.session_state.summary_text)
        
        # Кнопка скачивания
        summary_content, filename = download_summary_as_txt(st.session_state.summary_text, st.session_state.selected_prompt)
        
        st.download_button(
            label="💾 Скачать в TXT формате",
            data=summary_content,
            file_name=filename,
            mime="text/plain",
            use_container_width=True
        )
        
        # Кнопка для новой обработки
        if st.button("🔄 Обработать новый документ", use_container_width=True):
            st.session_state.summary_text = ""
            st.session_state.uploaded_file_content = ""
            st.session_state.file_uploaded = False
            st.rerun()

if __name__ == "__main__":
    main()
