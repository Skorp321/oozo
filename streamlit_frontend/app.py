import streamlit as st
import requests
import json
import time
from datetime import datetime
import markdown
from streamlit.components.v1 import html
import re

# Конфигурация страницы
st.set_page_config(
    page_title="Ассистент клиентского менеджера",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Конфигурация API
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
QUERY_ENDPOINT = f"{API_BASE_URL}/api/query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
STATS_ENDPOINT = f"{API_BASE_URL}/api/stats"
INFO_ENDPOINT = f"{API_BASE_URL}/api/info"

# CSS стили
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
        margin-left: 2rem;
    }
    
    .bot-message {
        background-color: #f5f5f5;
        border-left-color: #4caf50;
        margin-right: 2rem;
    }
    
    .error-message {
        background-color: #ffebee;
        border-left-color: #f44336;
    }
    
    .thinking-message {
        background-color: #fff3e0;
        border-left-color: #ff9800;
    }
    
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        color: #666;
    }
    
    .message-avatar {
        font-size: 1.2rem;
        margin-right: 0.5rem;
    }
    
    .sources-section {
        margin-top: 1rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 5px;
        border-left: 3px solid #007bff;
    }
    
    .source-item {
        margin: 0.5rem 0;
        padding: 0.5rem;
        background-color: white;
        border-radius: 3px;
        border: 1px solid #dee2e6;
    }
    
    .source-header {
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    
    .source-content {
        font-size: 0.9rem;
        color: #6c757d;
        max-height: 200px;
        overflow-y: auto;
    }
    
    .welcome-message {
        text-align: center;
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .loading-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        color: #666;
    }
    
    .typing-dots {
        display: inline-flex;
        margin-right: 0.5rem;
    }
    
    .typing-dots span {
        width: 8px;
        height: 8px;
        margin: 0 2px;
        background-color: #666;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
    }
    
    .stTextInput > div > div > input {
        border-radius: 20px;
    }
    
    .stButton > button {
        border-radius: 20px;
        background-color: #007bff;
        color: white;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: #0056b3;
    }
    
    .markdown-content {
        line-height: 1.6;
    }
    
    .markdown-content h1, .markdown-content h2, .markdown-content h3 {
        color: #1f77b4;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .markdown-content code {
        background-color: #f8f9fa;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
    
    .markdown-content pre {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        overflow-x: auto;
    }
    
    .markdown-content blockquote {
        border-left: 4px solid #007bff;
        padding-left: 1rem;
        margin: 1rem 0;
        color: #666;
    }
    
    .markdown-content table {
        border-collapse: collapse;
        width: 100%;
        margin: 1rem 0;
    }
    
    .markdown-content th, .markdown-content td {
        border: 1px solid #dee2e6;
        padding: 0.5rem;
        text-align: left;
    }
    
    .markdown-content th {
        background-color: #f8f9fa;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def check_backend_health():
    """Проверка состояния бэкенда"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=30)  # Увеличиваем до 30 секунд
        return response.status_code == 200
    except:
        return False

def send_message_to_api(question, return_sources=True):
    """Отправка сообщения в API"""
    try:
        response = requests.post(
            QUERY_ENDPOINT,
            json={
                "question": question,
                "return_sources": return_sources
            },
            timeout=600
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка API: {str(e)}")

def render_markdown(text):
    """Рендеринг markdown с кастомными стилями"""
    html_content = markdown.markdown(
        text,
        extensions=['fenced_code', 'tables', 'nl2br', 'codehilite']
    )
    return f'<div class="markdown-content">{html_content}</div>'

def display_message(sender, text, timestamp, sources=None, is_error=False, is_thinking=False):
    """Отображение сообщения в чате"""
    if sender == "user":
        avatar = "🧑"
        message_class = "user-message"
    elif is_thinking:
        avatar = "⏳"
        message_class = "thinking-message"
    elif is_error:
        avatar = "❌"
        message_class = "error-message"
    else:
        avatar = "🤖"
        message_class = "bot-message"
    
    st.markdown(f"""
    <div class="chat-message {message_class}">
        <div class="message-header">
            <span class="message-avatar">{avatar}</span>
            <span>{timestamp}</span>
        </div>
        {render_markdown(text)}
    </div>
    """, unsafe_allow_html=True)
    
    # Отображение источников
    if sources and len(sources) > 0:
        with st.expander(f"📚 Источники ({len(sources)})", expanded=False):
            for i, source in enumerate(sources):
                st.markdown(f"""
                <div class="source-item">
                    <div class="source-header">
                        #{i+1} - {source.get('metadata', {}).get('source', 'Неизвестный источник')}
                    </div>
                    <div class="source-content">
                        {render_markdown(source.get('content', ''))}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def main():
    # Заголовок
    st.markdown('<h1 class="main-header">🤖 Ассистент клиентского менеджера по вопросам залогов</h1>', unsafe_allow_html=True)
    
    # Проверка состояния бэкенда
    if not check_backend_health():
        st.error("⚠️ Бэкенд недоступен. Проверьте, что сервер запущен.")
        return
    
    # Инициализация сессии
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    
    # Приветственное сообщение
    if st.session_state.show_welcome and len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="welcome-message">
            <h2>Ассистент клиентского менеджера по вопросам залогов</h2>
            <p>Ассистент отвечает на вопросы связанные с документацией по залогам.</p>
            <p>По вопросам работы ассистента обращаться на почту <a href="mailto:Potapov.Sal@sberleasing.com">Potapov.Sal@sberleasing.com</a></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Отображение истории сообщений
    for message in st.session_state.messages:
        display_message(
            sender=message["sender"],
            text=message["text"],
            timestamp=message["timestamp"],
            sources=message.get("sources"),
            is_error=message.get("is_error", False),
            is_thinking=message.get("is_thinking", False)
        )
    
    # Индикатор загрузки
    if st.session_state.get("is_loading", False):
        st.markdown("""
        <div class="loading-indicator">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span>Бот обрабатывает запрос...</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Поле ввода
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Введите ваш вопрос:",
                key="user_input",
                disabled=st.session_state.get("is_loading", False),
                placeholder="Задайте вопрос о залогах...",
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")  # Пустая строка для выравнивания
            send_button = st.button(
                "Отправить",
                disabled=st.session_state.get("is_loading", False) or not user_input,
                use_container_width=True
            )
    
    # Обработка отправки сообщения
    if (send_button or (user_input and st.session_state.get("_enter_pressed", False))) and user_input:
        # Сброс флага
        st.session_state._enter_pressed = False
        
        # Добавление сообщения пользователя
        user_message = {
            "sender": "user",
            "text": user_input.strip(),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state.messages.append(user_message)
        
        # Скрытие приветственного сообщения
        st.session_state.show_welcome = False
        
        # Установка состояния загрузки
        st.session_state.is_loading = True
        
        # Добавление сообщения "думает"
        thinking_message = {
            "sender": "bot",
            "text": "Обрабатываю ваш запрос...",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "is_thinking": True
        }
        st.session_state.messages.append(thinking_message)
        
        # Перезагрузка страницы для отображения изменений
        st.rerun()
    
    # Обработка API запроса (если есть сообщение "думает")
    if st.session_state.messages and st.session_state.messages[-1].get("is_thinking"):
        try:
            # Удаление сообщения "думает"
            st.session_state.messages.pop()
            
            # Получение последнего сообщения пользователя
            user_message = next((msg for msg in reversed(st.session_state.messages) if msg["sender"] == "user"), None)
            
            if user_message:
                # Отправка запроса к API
                response = send_message_to_api(user_message["text"])
                
                # Добавление ответа бота
                bot_message = {
                    "sender": "bot",
                    "text": response.get("answer", "Извините, не удалось получить ответ."),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "sources": response.get("sources", [])
                }
                st.session_state.messages.append(bot_message)
                
        except Exception as e:
            # Удаление сообщения "думает"
            st.session_state.messages.pop()
            
            # Добавление сообщения об ошибке
            error_message = {
                "sender": "bot",
                "text": f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "is_error": True
            }
            st.session_state.messages.append(error_message)
        
        finally:
            # Сброс состояния загрузки
            st.session_state.is_loading = False
            st.rerun()
    
    # Обработка нажатия Enter
    if user_input and not send_button:
        st.session_state._enter_pressed = True

if __name__ == "__main__":
    main() 