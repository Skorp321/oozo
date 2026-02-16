"""
LangGraph React агент для HR системы
"""
import logging
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

import sys
from pathlib import Path

# Добавляем путь к backend для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools import AVAILABLE_TOOLS
from backend.config import settings

logger = logging.getLogger(__name__)


# Системный промпт для HR ассистента
SYSTEM_PROMPT = """Ты - полезный HR ассистент, который помогает сотрудникам с вопросами об отпусках, документации компании и корпоративных политиках.

Твои возможности:
1. Получение информации о персональных днях отпуска сотрудников
2. Получение информации об оставшихся днях основного отпуска
3. Поиск информации в корпоративных документах с помощью RAG

Важные правила:
- Всегда будь вежливым и профессиональным
- Если не знаешь ответа, используй инструмент rag_query для поиска в документах
- Для вопросов об отпусках используй соответствующие инструменты (get_personal_days, get_remaining_vacation_days)
- Отвечай на русском языке
- Если инструмент вернул ошибку, объясни пользователю что произошло

Используй инструменты когда это необходимо для ответа на вопрос пользователя."""


def create_hr_agent():
    """
    Создание LangGraph React агента для HR системы
    
    Returns:
        Скомпилированный граф агента
    """
    # Настройка LLM
    repo_id = settings.openai_model_name or "model-run-vekow-trunk"
    api_base = settings.openai_api_base or "https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1"
    
    llm = ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        openai_api_base=api_base,
        model=repo_id,
        temperature=settings.temperature,
        timeout=600
    )
    
    # Создание React агента
    agent = create_react_agent(
        llm,
        tools=AVAILABLE_TOOLS,
        state_modifier=SYSTEM_PROMPT
    )
    
    logger.info("HR агент создан успешно")
    return agent


# Глобальный экземпляр агента
_agent = None


def get_agent():
    """
    Получить или создать экземпляр агента
    
    Returns:
        Скомпилированный граф агента
    """
    global _agent
    if _agent is None:
        _agent = create_hr_agent()
    return _agent


def invoke_agent(user_message: str) -> str:
    """
    Вызвать агента с сообщением пользователя
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Ответ агента
    """
    try:
        agent = get_agent()
        
        # Создаем входное состояние для агента
        input_state = {
            "messages": [HumanMessage(content=user_message)]
        }
        
        logger.info(f"Обработка запроса пользователя: {user_message[:100]}...")
        
        # Вызываем агента
        result = agent.invoke(input_state)
        
        # Извлекаем последнее сообщение от агента
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                return last_message.content
            elif hasattr(last_message, "content"):
                return str(last_message.content)
        
        return "Не удалось получить ответ от агента"
        
    except Exception as e:
        logger.error(f"Ошибка при вызове агента: {e}")
        return f"Произошла ошибка при обработке запроса: {str(e)}"
