import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.rag_system import rag_system
from app.api import chat, system

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    # Startup
    logger.info("Запуск RAG системы...")
    try:
        # Инициализация RAG системы в фоновом режиме
        asyncio.create_task(initialize_rag_system())
        logger.info("RAG система запущена в фоновом режиме")
    except Exception as e:
        logger.error(f"Ошибка при запуске RAG системы: {e}")
    
    yield
    
    # Shutdown
    logger.info("Завершение работы RAG системы...")


async def initialize_rag_system():
    """
    Асинхронная инициализация RAG системы
    """
    try:
        # Инициализация в отдельном потоке для избежания блокировки
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, rag_system.initialize)
        logger.info("RAG система успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации RAG системы: {e}")


# Создание FastAPI приложения
app = FastAPI(
    title="RAG Oozo System",
    description="Система поиска и генерации ответов на основе документов",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:37113",  # порт, который выбрал serve
        "http://frontend:3000", 
        "http://10.77.98.1:3000",
        "http://10.77.98.1:37113"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Обработка ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Необработанная ошибка: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )


# Подключение роутеров
app.include_router(chat.router, tags=["chat"])
app.include_router(system.router, tags=["system"])


# Корневой эндпоинт
@app.get("/")
async def root():
    """
    Корневой эндпоинт с информацией о системе
    """
    return {
        "name": "RAG Oozo System",
        "version": "1.0.0",
        "description": "Система поиска и генерации ответов на основе документов",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# Проверка состояния системы
@app.get("/status")
async def status():
    """
    Проверка состояния системы
    """
    return {
        "rag_initialized": rag_system._initialized,
        "status": "healthy" if rag_system._initialized else "initializing"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 