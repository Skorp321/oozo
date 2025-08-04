from fastapi import APIRouter, HTTPException
from typing import List
import logging

from ..schemas import QueryRequest, QueryResponse, Source
from ..rag_system import rag_system

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Обработка запроса пользователя с использованием RAG системы
    """
    try:
        logger.info(f"Получен запрос: {request.question}")
        
        # Проверка инициализации системы
        if not rag_system._initialized:
            raise HTTPException(
                status_code=503,
                detail="RAG система не инициализирована"
            )
        
        # Выполнение запроса
        result = rag_system.query(
            question=request.question,
            return_sources=request.return_sources
        )
        
        # Формирование ответа
        response = QueryResponse(
            question=request.question,
            answer=result["answer"],
            sources=None
        )
        
        # Добавление источников если запрошено
        if request.return_sources and result.get("sources"):
            sources = []
            for source_data in result["sources"]:
                source = Source(
                    title=source_data["title"],
                    content=source_data["content"],
                    score=source_data["score"],
                    metadata=source_data.get("metadata")
                )
                sources.append(source)
            response.sources = sources
        
        logger.info(f"Запрос обработан успешно")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        ) 