from fastapi import APIRouter, HTTPException
from typing import List
import logging
import os
from pathlib import Path


from ..schemas import (
    HealthResponse, StatsResponse, InfoResponse, 
    SimilarityRequest, SimilarityResponse, IngestResponse, Source
)
from ..rag_system import rag_system
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Проверка состояния системы
    """
    try:
        status = "healthy" if rag_system._initialized else "initializing"
        message = "Система работает нормально" if rag_system._initialized else "Система инициализируется"
        
        return HealthResponse(status=status, message=message)
    except Exception as e:
        logger.error(f"Ошибка при проверке состояния: {e}")
        return HealthResponse(status="error", message=str(e))


@router.get("/api/info", response_model=InfoResponse)
async def get_info():
    """
    Информация о системе
    """
    try:
        return InfoResponse(
            name="RAG Oozo System",
            version="1.0.0",
            description="Система поиска и генерации ответов на основе документов",
            embedding_model=settings.embedding_model_name,
            llm_model=settings.openai_model_name
        )
    except Exception as e:
        logger.error(f"Ошибка при получении информации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """
    Статистика коллекции документов
    """
    try:
        if not rag_system._initialized:
            raise HTTPException(
                status_code=503,
                detail="RAG система не инициализирована"
            )
        
        stats = rag_system.get_stats()
        
        return StatsResponse(
            total_documents=stats.get("total_documents", 0),
            total_chunks=stats.get("total_chunks", 0),
            index_size_mb=stats.get("index_size_mb", 0.0),
            last_updated=stats.get("last_updated")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/similarity", response_model=SimilarityResponse)
async def similarity_search(request: SimilarityRequest):
    """
    Поиск похожих документов
    """
    try:
        if not rag_system._initialized:
            raise HTTPException(
                status_code=503,
                detail="RAG система не инициализирована"
            )
        
        results = rag_system.similarity_search(
            query=request.query,
            top_k=request.top_k
        )
        
        # Преобразование результатов в Source объекты
        sources = []
        for result in results:
            source = Source(
                title=result["title"],
                content=result["content"],
                score=result["score"],
                metadata=result.get("metadata")
            )
            sources.append(source)
        
        return SimilarityResponse(
            query=request.query,
            results=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при поиске похожих документов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest_documents():
    """
    Переиндексация документов
    """
    try:
        logger.info("Запуск переиндексации документов...")
        
        result = rag_system.reindex_documents()
        
        return IngestResponse(
            message=result["message"],
            documents_processed=result["documents_processed"],
            chunks_created=result["chunks_created"],
            index_size_mb=result["index_size_mb"]
        )
        
    except Exception as e:
        logger.error(f"Ошибка при переиндексации: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/documents")
async def list_documents():
    """
    Список доступных документов
    """
    try:
        docs_path = Path(settings.docs_path)
        
        if not docs_path.exists():
            return {"documents": [], "message": "Папка документов не найдена"}
        
        documents = []
        for file_path in docs_path.glob("*.docx"):
            try:
                stat = file_path.stat()
                documents.append({
                    "name": file_path.name,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "path": str(file_path)
                })
            except Exception as e:
                logger.warning(f"Ошибка при получении информации о файле {file_path}: {e}")
        
        return {
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка документов: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 