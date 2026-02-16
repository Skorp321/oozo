import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
import markdown

# Добавляем путь к agent для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.graph import invoke_agent

# Конфигурация страницы
st.set_page_config(
    page_title="HR Ассистент",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
        height: 44px;
    }
    
    .stButton > button {
        border-radius: 20px;
        background-color: #007bff;
        color: white;
        border: none;
        height: 44px;
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
</style>
""", unsafe_allow_html=True)


def render_markdown(text):
    """Рендеринг markdown с кастомными стилями"""
    html_content = markdown.markdown(
        text,
        extensions=['fenced_code', 'tables', 'nl2br', 'codehilite']
    )
    return f'<div class="markdown-content">{html_content}</div>'


def display_message(sender, text, timestamp, is_error=False):
    """Отображение сообщения в чате"""
    if sender == "user":
        avatar = "🧑"
        message_class = "user-message"
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


def main():
    # Заголовок
    st.markdown('<h1 class="main-header">🤖 HR Ассистент</h1>', unsafe_allow_html=True)
    
    # Инициализация сессии
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    
    # Инициализация служебных флагов
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    if "clear_input" not in st.session_state:
        st.session_state.clear_input = False
    
    # Приветственное сообщение
    if st.session_state.show_welcome and len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="welcome-message">
            <h2>HR Ассистент</h2>
            <p>Я помогу вам с вопросами об отпусках, документации компании и корпоративных политиках.</p>
            <p><strong>Примеры вопросов:</strong></p>
            <ul style="text-align: left; display: inline-block;">
                <li>Сколько персональных дней у alice?</li>
                <li>Сколько осталось дней отпуска у bob?</li>
                <li>Найди информацию о политике отпусков</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Отображение истории сообщений
    for message in st.session_state.messages:
        display_message(
            sender=message["sender"],
            text=message["text"],
            timestamp=message["timestamp"],
            is_error=message.get("is_error", False)
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
            <span>Агент обрабатывает запрос...</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Поле ввода + отправка
    with st.form("chat_form", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])

        with col1:
            # Если необходимо очистить поле ввода
            if st.session_state.get("clear_input"):
                st.session_state.user_input = ""
                st.session_state.clear_input = False
            user_input = st.text_input(
                "Введите ваш вопрос:",
                key="user_input",
                disabled=st.session_state.get("is_loading", False),
                placeholder="Задайте вопрос об отпусках или документации...",
                label_visibility="collapsed"
            )

        with col2:
            send_button = st.form_submit_button(
                "Отправить",
                disabled=st.session_state.get("is_loading", False),
                use_container_width=True
            )
    
    # Обработка отправки сообщения
    trimmed_input = (st.session_state.user_input or "").strip()
    if send_button and not trimmed_input:
        st.warning("Введите запрос!")
    if send_button and trimmed_input:
        # Добавление сообщения пользователя
        user_message = {
            "sender": "user",
            "text": trimmed_input,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state.messages.append(user_message)
        
        # Скрытие приветственного сообщения
        st.session_state.show_welcome = False
        
        # Установка состояния загрузки
        st.session_state.is_loading = True
        
        # Очистка поля ввода
        st.session_state.clear_input = True
        
        # Перезагрузка страницы для отображения изменений
        st.rerun()
    
    # Обработка API запроса (если есть сообщение пользователя и идет загрузка)
    if (st.session_state.messages and 
        st.session_state.messages[-1]["sender"] == "user" and 
        st.session_state.get("is_loading", False)):
        try:
            # Получение последнего сообщения пользователя
            user_message = st.session_state.messages[-1]
            
            # Вызов агента
            answer = invoke_agent(user_message["text"])
            
            # Добавление ответа агента
            bot_message = {
                "sender": "bot",
                "text": answer,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
            st.session_state.messages.append(bot_message)
                
        except Exception as e:
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


if __name__ == "__main__":
    main()
