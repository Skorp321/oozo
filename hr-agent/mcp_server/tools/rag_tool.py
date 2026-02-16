"""
RAG инструмент для поиска по документам
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Добавляем путь к backend для импорта
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.rag_system import rag_system
from .tool_base import MCPTool

logger = logging.getLogger(__name__)


class RAGTool(MCPTool):
    """
    Инструмент для поиска информации в документах с помощью RAG
    """
    
    def __init__(self):
        # Инициализируем RAG систему при создании инструмента
        if not rag_system._initialized:
            try:
                rag_system.initialize()
            except Exception as e:
                logger.error(f"Ошибка при инициализации RAG системы: {e}")
                raise
    
    @property
    def name(self) -> str:
        return "rag_query"
    
    @property
    def description(self) -> str:
        return "Поиск информации в документах с помощью RAG (Retrieval-Augmented Generation). Используйте этот инструмент для ответов на вопросы, связанные с документацией, политиками компании, процедурами и другой корпоративной информацией."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Вопрос или запрос для поиска в документах"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение RAG запроса
        
        Args:
            params: Словарь с параметром "query"
            
        Returns:
            Результат поиска с ответом и источниками
        """
        query = params.get("query")
        if not query:
            return {
                "error": "Параметр 'query' обязателен",
                "answer": None,
                "sources": []
            }
        
        try:
            logger.info(f"Выполнение RAG запроса: {query}")
            result = rag_system.query(query, return_sources=True)
            
            # Форматируем ответ для MCP
            response = {
                "answer": result.get("answer", "Не удалось получить ответ"),
                "sources": result.get("sources", []),
                "query": query
            }
            
            # Добавляем информацию об источниках в текстовый формат
            sources_text = ""
            if result.get("sources"):
                sources_text = "\n\nИсточники:\n"
                for i, source in enumerate(result["sources"], 1):
                    sources_text += f"{i}. {source.get('title', 'Неизвестный источник')}\n"
                    sources_text += f"   {source.get('content', '')[:200]}...\n"
            
            response["formatted_answer"] = response["answer"] + sources_text
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении RAG запроса: {e}")
            return {
                "error": str(e),
                "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
                "sources": [],
                "query": query
            }
