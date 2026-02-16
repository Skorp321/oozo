"""
Pydantic схемы для MCP сервера
"""
from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class ToolInfo(BaseModel):
    """Информация об инструменте"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ListToolsResponse(BaseModel):
    """Ответ на запрос списка инструментов"""
    tools: List[ToolInfo]


class ToolCallRequest(BaseModel):
    """Запрос на вызов инструмента"""
    name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    """Ответ на вызов инструмента"""
    content: List[Dict[str, Any]]
    isError: bool = False


class HealthResponse(BaseModel):
    """Ответ на проверку здоровья"""
    status: str
    message: str
