"""
Обертки для MCP инструментов для использования в LangGraph
"""
import requests
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

import os

# URL MCP сервера (можно настроить через переменную окружения)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Вызов инструмента через MCP сервер
    
    Args:
        tool_name: Имя инструмента
        arguments: Аргументы инструмента
        
    Returns:
        Результат выполнения инструмента
    """
    try:
        url = f"{MCP_SERVER_URL}/mcp/tools/call"
        payload = {
            "name": tool_name,
            "arguments": arguments
        }
        
        logger.info(f"Вызов MCP инструмента '{tool_name}' с аргументами: {arguments}")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("isError"):
            error_text = result.get("content", [{}])[0].get("text", "Неизвестная ошибка")
            logger.error(f"Ошибка при вызове инструмента '{tool_name}': {error_text}")
            return {"error": error_text}
        
        # Извлекаем текст из content
        content = result.get("content", [{}])[0].get("text", "")
        
        # Пытаемся распарсить JSON если это возможно
        try:
            import json
            parsed = json.loads(content)
            return parsed
        except:
            return {"result": content}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к MCP серверу: {e}")
        return {"error": f"Не удалось подключиться к MCP серверу: {str(e)}"}
    except Exception as e:
        logger.error(f"Неожиданная ошибка при вызове инструмента: {e}")
        return {"error": str(e)}


@tool
def rag_query(query: str) -> str:
    """
    Поиск информации в документах с помощью RAG.
    Используйте этот инструмент для ответов на вопросы, связанные с документацией,
    политиками компании, процедурами и другой корпоративной информацией.
    
    Args:
        query: Вопрос или запрос для поиска в документах
        
    Returns:
        Ответ на основе найденных документов
    """
    result = call_mcp_tool("rag_query", {"query": query})
    
    if "error" in result:
        return f"Ошибка: {result['error']}"
    
    # Форматируем ответ
    answer = result.get("answer") or result.get("formatted_answer") or result.get("result", "Не удалось получить ответ")
    
    # Добавляем источники если есть
    sources = result.get("sources", [])
    if sources:
        answer += "\n\nИсточники:"
        for i, source in enumerate(sources[:3], 1):  # Показываем только первые 3
            title = source.get("title", "Неизвестный источник")
            answer += f"\n{i}. {title}"
    
    return answer


@tool
def get_personal_days(employee_name: str) -> str:
    """
    Получить количество персональных дней отпуска для указанного сотрудника.
    Персональные дни - это дополнительные дни отпуска, предоставляемые сотруднику помимо основного отпуска.
    
    Args:
        employee_name: Имя сотрудника (например: alice, bob, charlie)
        
    Returns:
        Информация о персональных днях сотрудника
    """
    result = call_mcp_tool("get_personal_days", {"employee_name": employee_name})
    
    if "error" in result:
        return f"Ошибка: {result['error']}"
    
    message = result.get("message") or f"У сотрудника {employee_name} {result.get('personal_days', 0)} персональных дней отпуска"
    return message


@tool
def get_remaining_vacation_days(employee_name: str) -> str:
    """
    Получить количество оставшихся дней основного отпуска для указанного сотрудника.
    Возвращает разницу между общим количеством дней отпуска и уже использованными днями.
    
    Args:
        employee_name: Имя сотрудника (например: alice, bob, charlie)
        
    Returns:
        Информация об оставшихся днях отпуска сотрудника
    """
    result = call_mcp_tool("get_remaining_vacation_days", {"employee_name": employee_name})
    
    if "error" in result:
        return f"Ошибка: {result['error']}"
    
    message = result.get("message") or f"У сотрудника {employee_name} осталось {result.get('remaining_vacation_days', 0)} дней отпуска"
    return message


# Список всех доступных инструментов
AVAILABLE_TOOLS = [
    rag_query,
    get_personal_days,
    get_remaining_vacation_days
]
