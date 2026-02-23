import streamlit as st
import os
import logging

import requests
import json
import time
from datetime import datetime
import markdown
from streamlit.components.v1 import html
import re

_logger = logging.getLogger(__name__)

# Конфигурация страницы
st.set_page_config(
    page_title="Ассистент клиентского менеджера",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Конфигурация API (приоритет: переменная окружения > secrets > дефолт)
def get_api_base_url():
    """Получение базового URL API с правильным приоритетом"""
    # Сначала проверяем переменную окружения
    env_url = os.environ.get("API_BASE_URL")
    if env_url:
        return env_url
    
    # Затем проверяем secrets
    try:
        secrets_url = st.secrets.get("API_BASE_URL")
        if secrets_url:
            return secrets_url
    except:
        pass
    
    # Дефолт для Docker окружения
    return "http://rag-app:8000"

API_BASE_URL = get_api_base_url()
STREAM_QUERY_ENDPOINT = f"{API_BASE_URL}/api/query/stream"
QUERY_ENDPOINT = f"{API_BASE_URL}/api/query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
STATS_ENDPOINT = f"{API_BASE_URL}/api/stats"
INFO_ENDPOINT = f"{API_BASE_URL}/api/info"
FEEDBACK_ENDPOINT = f"{API_BASE_URL}/api/feedback"

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

    .message-time {
        margin-top: 0.5rem;
        font-size: 0.85rem;
        color: #666;
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
        height: 44px;
    }
    
    .stButton > button {
        border-radius: 20px;
        background-color: #007bff;
        color: white;
        border: none;
        height: 44px;
    }
    
    .stButton > button:hover {
        background-color: #007bff; /* оставляем синий при hover */
    }

    /* Принудительно делаем primary-кнопку синей (API Streamlit 1.4x) */
    button[data-testid="baseButton-primary"] {
        background-color: #007bff !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 20px !important;
        height: 44px !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        background-color: #007bff !important; /* оставляем синий при hover */
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
    
    .feedback-caption {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def check_backend_health():
    """Проверка состояния бэкенда"""
    try:
        # Используем актуальное значение API_BASE_URL
        current_api_url = get_api_base_url()
        health_url = f"{current_api_url}/health"
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError as e:
        # Логируем ошибку для отладки
        import logging
        logging.error(f"Не удалось подключиться к бэкенду по адресу {health_url}: {e}")
        return False
    except Exception as e:
        import logging
        logging.error(f"Ошибка при проверке бэкенда: {e}")
        return False

def send_message_to_api(question, return_sources=True):
    """Потоковая отправка в API (SSE). Возвращает объект Response для чтения потока."""
    try:
        # timeout=(connect, read): при стриме read — макс. время между приходами данных
        response = requests.post(
            STREAM_QUERY_ENDPOINT,
            stream=True,
            json={
                "question": question,
                "return_sources": False
            },
            headers={"Accept": "text/event-stream"},
            timeout=(10, 120)
        )
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout as e:
        raise Exception("Превышено время ожидания ответа от сервера. Попробуйте ещё раз или сократите вопрос.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка API: {str(e)}")

def render_markdown(text):
    """Рендеринг markdown с кастомными стилями"""
    html_content = markdown.markdown(
        text,
        extensions=['fenced_code', 'tables', 'nl2br', 'codehilite']
    )
    return f'<div class="markdown-content">{html_content}</div>'

def save_feedback_to_db(query_log_id: int, feedback: str) -> bool:
    """
    Отправляет оценку (like/dislike) по ID ответа из query_logs в бэкенд для сохранения в PostgreSQL.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        resp = requests.post(
            FEEDBACK_ENDPOINT,
            json={"query_log_id": query_log_id, "feedback": feedback},
            timeout=10,
        )
        resp.raise_for_status()
        _logger.info("Feedback сохранён в БД: query_log_id=%s, %s", query_log_id, feedback)
        return True
    except requests.RequestException as e:
        _logger.warning("Не удалось сохранить feedback в БД: %s", e)
        return False


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

    time_label = "Время получения ответа" if sender == "bot" and not is_thinking else "Время сообщения"
    
    st.markdown(f"""
    <div class="chat-message {message_class}">
        <div class="message-header">
            <span class="message-avatar">{avatar}</span>
        </div>
        {render_markdown(text)}
        <div class="message-time">{time_label}: {timestamp}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Отображение источников
    # if sources and len(sources) > 0:
    #     with st.expander(f"📚 Источники ({len(sources)})", expanded=False):
    #         for i, source in enumerate(sources):
    #             st.markdown(f"""
    #             <div class="source-item">
    #                 <div class="source-header">
    #                     #{i+1} - {source.get('metadata', {}).get('source', source.get('title', 'Неизвестный источник'))}
    #                 </div>
    #                 <div class="source-content">
    #                     {render_markdown(source.get('content', ''))}
    #                 </div>
    #             </div>
    #             """, unsafe_allow_html=True)

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
    
    # Инициализация служебных флагов и значения ввода ДО создания виджетов
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
            <h2>Ассистент клиентского менеджера по вопросам залогов</h2>
            <p>Ассистент отвечает на вопросы связанные с документацией по залогам.</p>
            <p>По вопросам работы ассистента обращаться на почту <a href="mailto:Potapov.Sal@sberleasing.com">Potapov.Sal@sberleasing.com</a></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Отображение истории сообщений
    for idx, message in enumerate(st.session_state.messages):
        display_message(
            sender=message["sender"],
            text=message["text"],
            timestamp=message["timestamp"],
            sources=message.get("sources"),
            is_error=message.get("is_error", False),
            is_thinking=message.get("is_thinking", False)
        )
        # Кнопки like/dislike под каждым ответом бота (кроме ошибок и служебного "думает")
        if (
            message["sender"] == "bot"
            and not message.get("is_error")
            and not message.get("is_thinking")
        ):
            feedback = message.get("feedback")
            if feedback:
                if feedback == "like":
                    st.markdown('<p class="feedback-caption">👍 Вам понравилось это сообщение</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p class="feedback-caption">👎 Вам не понравилось это сообщение</p>', unsafe_allow_html=True)
            else:
                query_log_id = message.get("query_log_id")
                if query_log_id is None:
                    st.markdown('<p class="feedback-caption">Оценка недоступна: ответ не сохранен в БД.</p>', unsafe_allow_html=True)
                else:
                    col_like, col_dislike, _ = st.columns([1, 1, 4])
                    with col_like:
                        if st.button("👍 Like", key=f"like_{idx}", use_container_width=True):
                            if save_feedback_to_db(query_log_id, "like"):
                                message["feedback"] = "like"
                                st.rerun()
                            else:
                                st.error("Не удалось сохранить оценку в БД.")
                    with col_dislike:
                        if st.button("👎 Dislike", key=f"dislike_{idx}", use_container_width=True):
                            if save_feedback_to_db(query_log_id, "dislike"):
                                message["feedback"] = "dislike"
                                st.rerun()
                            else:
                                st.error("Не удалось сохранить оценку в БД.")
    
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
    
    # Поле ввода + отправка (кнопка всегда активна; Enter отправляет форму)
    with st.form("chat_form", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])

        with col1:
            # Если необходимо очистить поле ввода, делаем это ДО создания виджета
            if st.session_state.get("clear_input"):
                st.session_state.user_input = ""
                st.session_state.clear_input = False
            user_input = st.text_input(
                "Введите ваш вопрос:",
                key="user_input",
                disabled=st.session_state.get("is_loading", False),
                placeholder="Задайте вопрос о залогах...",
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
        
        # Очистка поля ввода выполняется через флаг, чтобы сделать это ДО создания виджета
        st.session_state.clear_input = True
        
        # Добавление сообщения "думает"
        thinking_message = {
            "sender": "bot",
            "text": "Система 'АИСТ' летит к вам с ответом...",
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
                generated_text = ""
                sources_collected = None
                query_log_id = None
                resp = send_message_to_api(user_message["text"])  # потоковый Response
                if resp.status_code == 200:
                    word_container = st.empty()
                    for raw_line in resp.iter_lines(decode_unicode=True):
                        if not raw_line:
                            continue
                        line = raw_line.strip()
                        if line.startswith("data:"):
                            payload = line[len("data:"):].strip()
                        else:
                            payload = line
                        if payload == "[DONE]":
                            break
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(data, dict) and data.get("error"):
                            raise Exception(data["error"])
                        # ID ответа из query_logs для связи с оценками (like/dislike)
                        if isinstance(data, dict) and "query_log_id" in data:
                            query_log_id = data["query_log_id"]
                            continue
                        # Получение источников (чанков) из SSE
                        if isinstance(data, dict) and data.get("sources") is not None:
                            try:
                                if isinstance(data["sources"], list):
                                    sources_collected = data["sources"]
                                    st.info(f"Получены источники: {len(sources_collected)} чанков")
                            except Exception as e:
                                st.warning(f"Ошибка обработки источников: {e}")
                                sources_collected = None
                            continue
                        token = data.get("token") if isinstance(data, dict) else None
                        if token:
                            generated_text += token
                            word_container.markdown(f"**Генерация текста:** {generated_text.split('</think>')[-1]} ▋")
                    
                    if generated_text:
                        bot_message = {
                            "sender": "bot",
                            "text": generated_text.split('</think>')[-1],
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        }
                        if query_log_id is not None:
                            bot_message["query_log_id"] = query_log_id
                        if sources_collected:
                            bot_message["sources"] = sources_collected
                            st.success(f"Добавлены источники: {len(sources_collected)} чанков")
                        else:
                            st.warning("Источники не получены")
                        st.session_state.messages.append(bot_message)
                    else:
                        # Стрим завершился без текста (нет [DONE] или пустой ответ)
                        st.session_state.messages.append({
                            "sender": "bot",
                            "text": "Ответ не был получен. Проверьте, что бэкенд и индекс документов доступны, и попробуйте ещё раз.",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "is_error": True,
                        })
                
        except requests.exceptions.Timeout as e:
            # При таймауте используем частичный ответ, если он есть
            final_text = (generated_text or "").split('</think>')[-1].strip() if user_message else ""
            if len(final_text) > 50:
                bot_message = {
                    "sender": "bot",
                    "text": final_text + "\n\n_*(Ответ обрезан из-за таймаута. Попробуйте повторить запрос.)*_",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }
                if query_log_id is not None:
                    bot_message["query_log_id"] = query_log_id
                if sources_collected:
                    bot_message["sources"] = sources_collected
                st.session_state.messages.append(bot_message)
            else:
                st.session_state.messages.append({
                    "sender": "bot",
                    "text": "Превышено время ожидания ответа. Попробуйте ещё раз или сократите вопрос.",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "is_error": True,
                })
        except Exception as e:
            # Удаление сообщения "думает" (оно могло остаться при ошибке до pop)
            if st.session_state.messages and st.session_state.messages[-1].get("is_thinking"):
                st.session_state.messages.pop()
            # При другой ошибке — показываем частичный ответ, если есть
            final_text = (generated_text or "").split('</think>')[-1].strip() if user_message else ""
            if len(final_text) > 50:
                bot_message = {
                    "sender": "bot",
                    "text": final_text + "\n\n_*(Ответ может быть неполным из-за ошибки.)*_",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }
                if query_log_id is not None:
                    bot_message["query_log_id"] = query_log_id
                if sources_collected:
                    bot_message["sources"] = sources_collected
                st.session_state.messages.append(bot_message)
            else:
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
    
    # Enter также отправляет форму благодаря st.form

if __name__ == "__main__":
    main() 
