import os
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import logging
from contextlib import asynccontextmanager

from main import RAGSystem, health_check, VectorStoreManager
from config.settings import *

# Настройка логирования
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Глобальная переменная для RAG системы
rag_system: Optional[RAGSystem] = None

# Pydantic модели для API с детальными описаниями
class QueryRequest(BaseModel):
    """
    Запрос для обработки вопроса через RAG систему
    """
    question: str = Field(
        ...,
        description="Вопрос пользователя для обработки",
        example="Что такое машинное обучение?",
        min_length=1,
        max_length=1000
    )
    return_sources: bool = Field(
        True,
        description="Возвращать ли источники документов в ответе",
        example=True
    )

    class Config:
        schema_extra = {
            "example": {
                "question": "Объясните принципы работы нейронных сетей",
                "return_sources": True
            }
        }

class QueryResponse(BaseModel):
    """
    Ответ на запрос с сгенерированным ответом и источниками
    """
    answer: str = Field(
        ...,
        description="Сгенерированный ответ на основе найденных документов",
        example="Нейронные сети - это вычислительные модели, вдохновленные биологическими нейронными сетями..."
    )
    question: str = Field(
        ...,
        description="Исходный вопрос пользователя",
        example="Объясните принципы работы нейронных сетей"
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Список источников документов, использованных для генерации ответа",
        example=[
            {
                "content": "Нейронные сети состоят из слоев нейронов...",
                "metadata": {
                    "source": "/app/documents/ai_basics.txt",
                    "chunk_title": "Введение в нейронные сети",
                    "section_number": 1
                }
            }
        ]
    )

    class Config:
        schema_extra = {
            "example": {
                "answer": "Нейронные сети - это вычислительные модели, вдохновленные биологическими нейронными сетями. Они состоят из слоев взаимосвязанных узлов (нейронов), которые обрабатывают информацию и учатся на примерах.",
                "question": "Объясните принципы работы нейронных сетей",
                "sources": [
                    {
                        "content": "Нейронные сети состоят из слоев нейронов, каждый из которых выполняет определенные вычисления...",
                        "metadata": {
                            "source": "/app/documents/ai_basics.txt",
                            "chunk_title": "Введение в нейронные сети",
                            "section_number": 1
                        }
                    }
                ]
            }
        }

class SimilarityRequest(BaseModel):
    """
    Запрос для поиска похожих документов
    """
    query: str = Field(
        ...,
        description="Поисковый запрос для поиска похожих документов",
        example="машинное обучение алгоритмы",
        min_length=1,
        max_length=500
    )
    k: int = Field(
        4,
        description="Количество возвращаемых документов",
        ge=1,
        le=20,
        example=5
    )

    class Config:
        schema_extra = {
            "example": {
                "query": "машинное обучение алгоритмы",
                "k": 5
            }
        }

class HealthResponse(BaseModel):
    """
    Ответ с информацией о состоянии системы
    """
    status: str = Field(
        ...,
        description="Общий статус системы",
        example="ok",
        pattern="^(ok|degraded|error|critical_error|connection_error)$"
    )
    timestamp: str = Field(
        ...,
        description="Временная метка проверки",
        example="2025-07-31T23:51:49.793152"
    )
    components: Dict[str, str] = Field(
        ...,
        description="Состояние отдельных компонентов системы",
        example={
            "mistral_api_key": "valid",
            "embedding_model": "loaded",
            "database": "connected",
            "environment": "complete"
        }
    )
    issues: List[str] = Field(
        default_factory=list,
        description="Список проблем, если есть",
        example=[]
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Рекомендации по устранению проблем",
        example=[]
    )
    priority_issue: Optional[str] = Field(
        None,
        description="Приоритетная проблема, если есть",
        example="MISTRAL_API_KEY"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2025-07-31T23:51:49.793152",
                "components": {
                    "mistral_api_key": "valid",
                    "embedding_model": "loaded",
                    "database": "connected",
                    "environment": "complete"
                },
                "issues": [],
                "recommendations": []
            }
        }

class StatsResponse(BaseModel):
    """
    Статистика векторного хранилища
    """
    document_count: int = Field(
        ...,
        description="Количество документов в хранилище",
        example=137
    )
    table_size: str = Field(
        ...,
        description="Размер таблицы в читаемом формате",
        example="2.5 MB"
    )
    collection_name: str = Field(
        ...,
        description="Название коллекции",
        example="rag_collection"
    )

    class Config:
        schema_extra = {
            "example": {
                "document_count": 137,
                "table_size": "2.5 MB",
                "collection_name": "rag_collection"
            }
        }

class IngestRequest(BaseModel):
    """
    Запрос для загрузки новых документов
    """
    file_path: str = Field(
        ...,
        description="Путь к файлу или директории для загрузки",
        example="/app/documents/new_docs"
    )
    chunk_size: int = Field(
        1000,
        description="Размер чанка для разделения документов",
        ge=100,
        le=2000,
        example=512
    )
    chunk_overlap: int = Field(
        200,
        description="Перекрытие между чанками",
        ge=0,
        le=500,
        example=64
    )

    class Config:
        schema_extra = {
            "example": {
                "file_path": "/app/documents/new_docs",
                "chunk_size": 512,
                "chunk_overlap": 64
            }
        }

class SimilarityResponse(BaseModel):
    """
    Ответ на запрос поиска похожих документов
    """
    results: List[Dict[str, Any]] = Field(
        ...,
        description="Список найденных документов",
        example=[
            {
                "content": "Машинное обучение - это подраздел искусственного интеллекта...",
                "metadata": {
                    "source": "/app/documents/ai_basics.txt",
                    "chunk_title": "Введение в машинное обучение"
                }
            }
        ]
    )
    count: int = Field(
        ...,
        description="Количество найденных документов",
        example=5
    )

    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "content": "Машинное обучение - это подраздел искусственного интеллекта...",
                        "metadata": {
                            "source": "/app/documents/ai_basics.txt",
                            "chunk_title": "Введение в машинное обучение"
                        }
                    }
                ],
                "count": 1
            }
        }

class IngestResponse(BaseModel):
    """
    Ответ на запрос загрузки документов
    """
    message: str = Field(
        ...,
        description="Сообщение о результате операции",
        example="Документы успешно загружены"
    )
    documents_count: int = Field(
        ...,
        description="Количество обработанных документов",
        example=5
    )
    chunks_count: int = Field(
        ...,
        description="Количество созданных чанков",
        example=25
    )
    semantic_chunks: int = Field(
        ...,
        description="Количество семантических чанков",
        example=20
    )
    fallback_chunks: int = Field(
        ...,
        description="Количество fallback чанков",
        example=5
    )

    class Config:
        schema_extra = {
            "example": {
                "message": "Документы успешно загружены",
                "documents_count": 5,
                "chunks_count": 25,
                "semantic_chunks": 20,
                "fallback_chunks": 5
            }
        }

class SystemInfoResponse(BaseModel):
    """
    Информация о конфигурации системы
    """
    embedding_model: str = Field(
        ...,
        description="Название модели эмбеддингов",
        example="intfloat/e5-base-v2"
    )
    llm_model: str = Field(
        ...,
        description="Название языковой модели",
        example="mistral-small"
    )
    collection_name: str = Field(
        ...,
        description="Название коллекции в векторном хранилище",
        example="rag_collection"
    )
    chunk_size: int = Field(
        ...,
        description="Размер чанка",
        example=512
    )
    chunk_overlap: int = Field(
        ...,
        description="Перекрытие чанков",
        example=64
    )
    similarity_search_k: int = Field(
        ...,
        description="Количество результатов поиска",
        example=5
    )
    system_initialized: bool = Field(
        ...,
        description="Статус инициализации системы",
        example=True
    )

    class Config:
        schema_extra = {
            "example": {
                "embedding_model": "intfloat/e5-base-v2",
                "llm_model": "mistral-small",
                "collection_name": "rag_collection",
                "chunk_size": 512,
                "chunk_overlap": 64,
                "similarity_search_k": 5,
                "system_initialized": True
            }
        }

# Функция инициализации RAG системы с fallback механизмом
async def initialize_rag_system():
    """Инициализация RAG системы при запуске приложения с graceful degradation"""
    global rag_system
    
    # Проверяем API ключ перед инициализацией
    mistral_key = MISTRAL_API_KEY or LLM_API_KEY
    if not mistral_key or mistral_key.strip() == "" or mistral_key == "your_actual_mistral_api_key_here":
        logger.error("MISTRAL_API_KEY не настроен. Система будет работать в ограниченном режиме.")
        logger.error("Получите API ключ на https://console.mistral.ai/ и установите переменную MISTRAL_API_KEY")
        return  # Не инициализируем систему без API ключа
    
    try:
        logger.info("Инициализация RAG системы...")
        
        # Создание экземпляра RAG системы
        try:
            rag_system = RAGSystem(
                db_connection_string=DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"),
                collection_name=VECTOR_STORE_COLLECTION_NAME,
                embedding_model=EMBEDDING_MODEL_NAME,
                llm_model=LLM_MODEL_NAME
            )
            logger.info("RAGSystem создан успешно")
        except Exception as e:
            logger.error(f"Ошибка создания RAGSystem: {e}")
            if "api_key" in str(e).lower() or "mistral" in str(e).lower():
                logger.error("Проблема с Mistral API ключом. Проверьте корректность MISTRAL_API_KEY")
            raise
        
        # Настройка базы данных
        try:
            await rag_system.setup_database()
            logger.info("База данных настроена")
        except Exception as e:
            logger.error(f"Ошибка настройки базы данных: {e}")
            logger.error("Проверьте работу PostgreSQL контейнера: docker compose ps postgres-pgvector")
            raise
        
        # Инициализация векторного хранилища
        try:
            rag_system.initialize_vector_store()
            logger.info("Векторное хранилище инициализировано")
        except Exception as e:
            logger.error(f"Ошибка инициализации векторного хранилища: {e}")
            raise
        
        # Проверка наличия документов в директории
        documents_dir = "/app/documents" 
        local_documents_dir = "./documents"
        
        # Выбираем существующую директорию
        if os.path.exists(documents_dir):
            docs_path = documents_dir
        elif os.path.exists(local_documents_dir):
            docs_path = local_documents_dir
        else:
            docs_path = None
            
        if docs_path and os.listdir(docs_path):
            logger.info(f"Загрузка документов из {docs_path}")
            
            try:
                # Загрузка документов
                documents = rag_system.load_documents(docs_path)
                
                if documents:
                    # Разделение документов на чанки
                    split_docs = rag_system.split_documents(
                        documents, 
                        chunk_size=CHUNK_SIZE, 
                        chunk_overlap=CHUNK_OVERLAP
                    )
                    
                    # Добавление документов в векторное хранилище
                    await rag_system.add_documents_to_vector_store(split_docs)
                    logger.info("Документы добавлены в векторное хранилище")
                else:
                    logger.warning("Документы не найдены для загрузки")
            except Exception as e:
                logger.error(f"Ошибка загрузки документов: {e}")
                logger.warning("Система будет работать без предзагруженных документов")
        else:
            logger.warning(f"Директория документов не найдена или пуста. Проверено: {documents_dir}, {local_documents_dir}")
            logger.info("Система будет работать без предзагруженных документов")
        
        # Создание ретривера
        try:
            rag_system.create_retriever(
                search_type="similarity", 
                k=SIMILARITY_SEARCH_K
            )
            logger.info("Ретривер создан")
        except Exception as e:
            logger.error(f"Ошибка создания ретривера: {e}")
            raise
        
        # Создание QA цепочки
        try:
            custom_prompt = """
            Ты - полезный ассистент. Используй предоставленный контекст для ответа на вопрос.
            Отвечай точно и по существу на русском языке. Если информации недостаточно, скажи об этом.
            
            Контекст: {context}
            
            Вопрос: {question}
            
            Подробный ответ:
            """
            rag_system.create_qa_chain(custom_prompt)
            logger.info("QA цепочка создана")
        except Exception as e:
            logger.error(f"Ошибка создания QA цепочки: {e}")
            raise
        
        logger.info("RAG система успешно инициализирована")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации RAG системы: {e}")
        logger.error("Система будет недоступна. Проверьте:")
        logger.error("1. Корректность MISTRAL_API_KEY")
        logger.error("2. Работу PostgreSQL: docker compose ps")
        logger.error("3. Логи контейнеров: docker compose logs")
        rag_system = None  # Обнуляем систему при ошибке
        # Не поднимаем исключение - позволяем приложению запуститься для диагностики

# Контекстный менеджер для управления жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_rag_system()
    yield
    # Shutdown
    logger.info("Завершение работы приложения")

# Создание FastAPI приложения с подробной документацией
app = FastAPI(
    title="RAG System API",
    description="""
# 🤖 RAG System API - Система поиска с дополненной генерацией

Это API для системы Retrieval-Augmented Generation (RAG), которая объединяет векторный поиск документов с генерацией ответов на основе языковых моделей.

## 🔧 Основные возможности

- **Векторный поиск**: Семантический поиск по документам с использованием эмбеддингов
- **Генерация ответов**: Создание ответов на основе найденных документов с помощью Mistral AI
- **Управление документами**: Загрузка, индексация и переиндексация документов
- **Мониторинг**: Детальная диагностика состояния системы и статистика

## 🏗️ Архитектура

- **Backend**: FastAPI + Python
- **База данных**: PostgreSQL с расширением pgvector
- **Embedding модель**: intfloat/e5-base-v2
- **LLM**: Mistral AI API
- **Frontend**: React

## 🔑 Аутентификация

API не требует аутентификации, но требует настройки `MISTRAL_API_KEY` в переменных окружения.

## 📊 Коды ответов

- `200` - Успешный запрос
- `206` - Частичный ответ (система работает с ограничениями)
- `400` - Неверный запрос
- `404` - Ресурс не найден
- `503` - Сервис недоступен
- `500` - Внутренняя ошибка сервера

## 🚀 Быстрый старт

1. Убедитесь, что система запущена: `docker compose up -d`
2. Проверьте состояние: `GET /health`
3. Отправьте запрос: `POST /api/query`

## 📝 Примеры использования

### Проверка состояния системы
```bash
curl http://localhost:8000/health
```

### Отправка запроса
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Что такое машинное обучение?", "return_sources": True}'
```

### Поиск похожих документов
```bash
curl -X POST "http://localhost:8000/api/similarity" \
  -H "Content-Type: application/json" \
  -d '{"query": "нейронные сети", "k": 5}'
```
    """,
    version="1.0.0",
    contact={
        "name": "RAG System Support",
        "url": "https://github.com/your-repo/rag-system",
        "email": "support@rag-system.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:80",    # Production frontend
        "http://localhost:443",   # Production HTTPS
        "http://frontend:3000",   # Docker frontend service
        "*"  # Разрешить все источники для разработки
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка состояния системы",
    description="""
    ## 🔍 Проверка состояния системы
    
    Этот endpoint предоставляет детальную диагностику всех компонентов RAG системы:
    
    - **Mistral API ключ**: Проверка валидности и доступности API ключа
    - **Embedding модель**: Статус загрузки модели эмбеддингов
    - **База данных**: Подключение к PostgreSQL с pgvector
    - **Переменные окружения**: Проверка конфигурации
    
    ## 📊 Возможные статусы
    
    - `ok` - Все компоненты работают корректно
    - `degraded` - Система работает с ограничениями
    - `error` - Критические проблемы
    - `critical_error` - Система недоступна
    
    ## 🔧 Использование
    
    ```bash
    curl http://localhost:8000/health
    ```
    
    ## 📝 Пример ответа
    
    ```json
    {
      "status": "ok",
      "timestamp": "2025-07-31T23:51:49.793152",
      "components": {
        "mistral_api_key": "valid",
        "embedding_model": "loaded",
        "database": "connected",
        "environment": "complete"
      },
      "issues": [],
      "recommendations": []
    }
    ```
    """,
    responses={
        200: {
            "description": "Система работает корректно",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "timestamp": "2025-07-31T23:51:49.793152",
                        "components": {
                            "mistral_api_key": "valid",
                            "embedding_model": "loaded",
                            "database": "connected",
                            "environment": "complete"
                        },
                        "issues": [],
                        "recommendations": []
                    }
                }
            }
        },
        206: {
            "description": "Система работает с ограничениями",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "timestamp": "2025-07-31T23:51:49.793152",
                        "components": {
                            "mistral_api_key": "valid",
                            "embedding_model": "loaded",
                            "database": "connected",
                            "environment": "complete"
                        },
                        "issues": ["Fallback модель используется"],
                        "recommendations": ["Проверьте интернет соединение"]
                    }
                }
            }
        },
        503: {
            "description": "Система недоступна",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "timestamp": "2025-07-31T23:51:49.793152",
                        "components": {
                            "mistral_api_key": "missing",
                            "embedding_model": "error",
                            "database": "error",
                            "environment": "incomplete"
                        },
                        "issues": ["MISTRAL_API_KEY не настроен"],
                        "recommendations": ["Получите API ключ на https://console.mistral.ai/"]
                    }
                }
            }
        }
    },
    tags=["Мониторинг"]
)
async def health_endpoint():
    """
    Расширенная проверка состояния системы с детальной диагностикой
    
    Выполняет комплексную проверку всех компонентов RAG системы:
    - Валидация Mistral API ключа
    - Проверка загрузки embedding модели
    - Тестирование подключения к базе данных
    - Валидация переменных окружения
    
    Возвращает детальную информацию о состоянии каждого компонента
    и рекомендации по устранению проблем.
    """
    try:
        health_result = health_check()
        
        # Определяем HTTP код ответа на основе статуса
        if health_result["status"] == "ok":
            status_code = 200
        elif health_result["status"] == "degraded":
            status_code = 206  # Partial Content - система работает но есть проблемы
        else:  # error
            status_code = 503  # Service Unavailable
        
        # Логируем результат
        if health_result["status"] == "error":
            logger.error(f"Health check failed: {health_result['issues']}")
        elif health_result["status"] == "degraded":
            logger.warning(f"Health check degraded: {health_result['issues']}")
        else:
            logger.info("Health check passed")
        
        # Создаем объект ответа
        response_data = {
            "status": health_result["status"],
            "timestamp": datetime.now().isoformat(),
            "components": health_result["components"],
            "issues": health_result["issues"],
            "recommendations": health_result["recommendations"]
        }
        
        # Добавляем приоритетную проблему если есть
        if "priority_issue" in health_result:
            response_data["priority_issue"] = health_result["priority_issue"]
        
        return HealthResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при проверке здоровья: {e}")
        error_response = {
            "status": "critical_error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "recommendations": [
                "Проверьте работу всех компонентов системы",
                "Просмотрите логи контейнеров: docker compose logs rag-app"
            ]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False, indent=2),
            status_code=500,
            media_type="application/json"
        )

@app.post(
    "/api/query",
    response_model=QueryResponse,
    summary="Обработка запроса через RAG систему",
    description="""
    ## 🤖 Основной endpoint для RAG системы
    
    Этот endpoint обрабатывает вопросы пользователей через систему Retrieval-Augmented Generation:
    
    1. **Векторный поиск**: Находит релевантные документы по семантическому сходству
    2. **Генерация ответа**: Создает ответ на основе найденных документов с помощью Mistral AI
    3. **Возврат источников**: Предоставляет источники документов для прозрачности
    
    ## 🔄 Процесс обработки
    
    1. Вопрос пользователя преобразуется в векторное представление
    2. Выполняется поиск похожих документов в векторном хранилище
    3. Найденные документы передаются в языковую модель
    4. Генерируется ответ на основе контекста и вопроса
    5. Возвращается ответ с источниками (опционально)
    
    ## 📝 Примеры запросов
    
    - "Что такое машинное обучение?"
    - "Объясните принципы работы нейронных сетей"
    - "Какие алгоритмы используются в компьютерном зрении?"
    
    ## ⚠️ Ограничения
    
    - Максимальная длина вопроса: 1000 символов
    - Требуется валидный MISTRAL_API_KEY
    - Система должна быть инициализирована
    """,
    responses={
        200: {
            "description": "Успешная обработка запроса",
            "content": {
                "application/json": {
                    "example": {
                        "answer": "Машинное обучение - это подраздел искусственного интеллекта, который позволяет компьютерам учиться на данных без явного программирования. Алгоритмы машинного обучения анализируют большие объемы данных, выявляют закономерности и используют их для принятия решений или прогнозирования.",
                        "question": "Что такое машинное обучение?",
                        "sources": [
                            {
                                "content": "Машинное обучение - это подраздел искусственного интеллекта...",
                                "metadata": {
                                    "source": "/app/documents/ai_basics.txt",
                                    "chunk_title": "Введение в машинное обучение",
                                    "section_number": 1
                                }
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Неверный запрос",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Вопрос не может быть пустым"
                    }
                }
            }
        },
        503: {
            "description": "RAG система не инициализирована",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RAG система не инициализирована"
                    }
                }
            }
        },
        500: {
            "description": "Ошибка обработки запроса",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Ошибка при обработке запроса: Не удалось подключиться к Mistral API"
                    }
                }
            }
        }
    },
    tags=["RAG"]
)
async def query_endpoint(request: QueryRequest):
    """
    Основной endpoint для обработки запросов к RAG системе
    
    Принимает вопрос пользователя и возвращает сгенерированный ответ
    на основе релевантных документов из векторного хранилища.
    
    Args:
        request: Запрос с вопросом и параметрами
        
    Returns:
        QueryResponse: Ответ с сгенерированным текстом и источниками
        
    Raises:
        HTTPException: При ошибках инициализации или обработки
    """
    global rag_system
    
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG система не инициализирована"
        )
    
    try:
        logger.info(f"Получен запрос: {request.question}")
        result = await rag_system.query(
            question=request.question,
            return_sources=request.return_sources
        )
        
        response = QueryResponse(
            answer=result["answer"],
            question=result["question"],
            sources=result.get("sources")
        )
        
        logger.info(f"Ответ сгенерирован для запроса: {request.question}")
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )

@app.post(
    "/api/similarity",
    response_model=SimilarityResponse,
    summary="Поиск похожих документов",
    description="""
    ## 🔍 Поиск похожих документов
    
    Этот endpoint выполняет прямой поиск документов по семантическому сходству
    без генерации ответа. Полезен для:
    
    - Исследования содержимого базы знаний
    - Поиска релевантных документов
    - Анализа качества индексации
    - Отладки системы
    
    ## 🔄 Процесс поиска
    
    1. Запрос преобразуется в векторное представление
    2. Выполняется поиск по косинусному сходству в векторном хранилище
    3. Результаты дедуплицируются и ранжируются
    4. Возвращается список релевантных документов
    
    ## 📊 Параметры поиска
    
    - `query`: Поисковый запрос (1-500 символов)
    - `k`: Количество результатов (1-20)
    
    ## 🎯 Примеры использования
    
    - Поиск документов по теме: "нейронные сети"
    - Исследование концепций: "машинное обучение алгоритмы"
    - Анализ содержимого: "компьютерное зрение"
    """,
    responses={
        200: {
            "description": "Успешный поиск",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "content": "Нейронные сети - это вычислительные модели, вдохновленные биологическими нейронными сетями. Они состоят из слоев взаимосвязанных узлов (нейронов), которые обрабатывают информацию и учатся на примерах.",
                                "metadata": {
                                    "source": "/app/documents/ai_basics.txt",
                                    "chunk_title": "Введение в нейронные сети",
                                    "section_number": 1
                                }
                            }
                        ],
                        "count": 1
                    }
                }
            }
        },
        400: {
            "description": "Неверный запрос",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Запрос не может быть пустым"
                    }
                }
            }
        },
        503: {
            "description": "RAG система не инициализирована",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RAG система не инициализирована"
                    }
                }
            }
        }
    },
    tags=["Поиск"]
)
async def similarity_endpoint(request: SimilarityRequest):
    """
    Endpoint для прямого поиска документов по семантическому сходству
    
    Выполняет поиск в векторном хранилище без генерации ответа.
    Возвращает список документов, наиболее похожих на запрос.
    
    Args:
        request: Запрос с поисковым текстом и количеством результатов
        
    Returns:
        SimilarityResponse: Список найденных документов с метаданными
        
    Raises:
        HTTPException: При ошибках инициализации или поиска
    """
    global rag_system
    
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG система не инициализирована"
        )
    
    try:
        documents = await rag_system.similarity_search(
            query=request.query,
            k=request.k
        )
        
        results = []
        for doc in documents:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return SimilarityResponse(results=results, count=len(results))
        
    except Exception as e:
        logger.error(f"Ошибка при поиске по схожести: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске по схожести: {str(e)}"
        )

@app.get(
    "/api/stats",
    response_model=StatsResponse,
    summary="Статистика векторного хранилища",
    description="""
    ## 📊 Статистика векторного хранилища
    
    Этот endpoint предоставляет статистическую информацию о состоянии
    векторного хранилища и индексированных документах.
    
    ## 📈 Показатели
    
    - **document_count**: Количество документов в хранилище
    - **table_size**: Размер таблицы в читаемом формате
    - **collection_name**: Название коллекции
    
    ## 🔍 Использование
    
    Полезно для:
    - Мониторинга размера базы знаний
    - Отслеживания роста данных
    - Диагностики производительности
    - Планирования ресурсов
    
    ## 📝 Пример ответа
    
    ```json
    {
      "document_count": 137,
      "table_size": "2.5 MB",
      "collection_name": "rag_collection"
    }
    ```
    """,
    responses={
        200: {
            "description": "Статистика успешно получена",
            "content": {
                "application/json": {
                    "example": {
                        "document_count": 137,
                        "table_size": "2.5 MB",
                        "collection_name": "rag_collection"
                    }
                }
            }
        },
        503: {
            "description": "RAG система не инициализирована",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RAG система не инициализирована"
                    }
                }
            }
        },
        500: {
            "description": "Ошибка получения статистики",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Ошибка при получении статистики: Не удалось подключиться к базе данных"
                    }
                }
            }
        }
    },
    tags=["Мониторинг"]
)
async def stats_endpoint():
    """
    Получение статистики векторного хранилища
    
    Возвращает информацию о количестве документов, размере таблицы
    и названии коллекции в векторном хранилище.
    
    Returns:
        StatsResponse: Статистическая информация о хранилище
        
    Raises:
        HTTPException: При ошибках инициализации или доступа к БД
    """
    global rag_system
    
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG система не инициализирована"
        )
    
    try:
        manager = VectorStoreManager(rag_system)
        stats = await manager.get_collection_stats()
        
        return StatsResponse(
            document_count=stats["document_count"],
            table_size=stats["table_size"],
            collection_name=rag_system.collection_name
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики: {str(e)}"
        )

@app.post(
    "/api/ingest",
    response_model=IngestResponse,
    summary="Загрузка новых документов",
    description="""
    ## 📥 Загрузка новых документов
    
    Этот endpoint позволяет загружать новые документы в векторное хранилище
    для расширения базы знаний системы.
    
    ## 🔄 Процесс загрузки
    
    1. **Чтение документов**: Загрузка файлов из указанного пути
    2. **Разделение на чанки**: Разбиение документов на фрагменты
    3. **Создание эмбеддингов**: Преобразование в векторные представления
    4. **Сохранение в БД**: Запись в PostgreSQL с pgvector
    
    ## 📁 Поддерживаемые форматы
    
    - `.txt` - Текстовые файлы
    - `.md` - Markdown файлы
    - Директории с документами
    
    ## ⚙️ Параметры обработки
    
    - `file_path`: Путь к файлу или директории
    - `chunk_size`: Размер чанка (100-2000 символов)
    - `chunk_overlap`: Перекрытие чанков (0-500 символов)
    
    ## 🎯 Примеры использования
    
    ```bash
    # Загрузка отдельного файла
    curl -X POST "http://localhost:8000/api/ingest" \
      -H "Content-Type: application/json" \
      -d '{"file_path": "/app/documents/new_article.txt"}'
    
    # Загрузка директории с кастомными параметрами
    curl -X POST "http://localhost:8000/api/ingest" \
      -H "Content-Type: application/json" \
      -d '{"file_path": "/app/documents/manual", "chunk_size": 800, "chunk_overlap": 100}'
    ```
    """,
    responses={
        200: {
            "description": "Документы успешно загружены",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Документы успешно загружены",
                        "documents_count": 5,
                        "chunks_count": 25,
                        "semantic_chunks": 20,
                        "fallback_chunks": 5
                    }
                }
            }
        },
        400: {
            "description": "Неверный запрос или документы не найдены",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Документы не найдены для загрузки"
                    }
                }
            }
        },
        404: {
            "description": "Файл не найден",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Файл не найден: /app/documents/nonexistent.txt"
                    }
                }
            }
        },
        503: {
            "description": "RAG система не инициализирована",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RAG система не инициализирована"
                    }
                }
            }
        }
    },
    tags=["Управление документами"]
)
async def ingest_endpoint(request: IngestRequest):
    """
    Endpoint для загрузки новых документов в векторное хранилище
    
    Загружает документы из указанного пути, разделяет их на чанки,
    создает векторные представления и сохраняет в базу данных.
    
    Args:
        request: Запрос с путем к документам и параметрами обработки
        
    Returns:
        IngestResponse: Результат загрузки с статистикой
        
    Raises:
        HTTPException: При ошибках загрузки или обработки документов
    """
    global rag_system
    
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG система не инициализирована"
        )
    
    try:
        if not os.path.exists(request.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Файл не найден: {request.file_path}"
            )
        
        # Загрузка документов из указанного пути
        documents = rag_system.load_documents(request.file_path)
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Документы не найдены для загрузки"
            )
        
        # Разделение документов на чанки
        split_docs = rag_system.split_documents(
            documents,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Добавление документов в векторное хранилище
        await rag_system.add_documents_to_vector_store(split_docs)
        
        return IngestResponse(
            message="Документы успешно загружены",
            documents_count=len(documents),
            chunks_count=len(split_docs),
            semantic_chunks=len([d for d in split_docs if d.metadata.get('chunk_type') == 'semantic']),
            fallback_chunks=len([d for d in split_docs if d.metadata.get('chunk_type') == 'fallback'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке документов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке документов: {str(e)}"
        )

@app.post(
    "/api/reindex",
    response_model=IngestResponse,
    summary="Полная переиндексация документов",
    description="""
    ## 🔄 Переиндексация документов
    
    Этот endpoint выполняет полную переиндексацию всех документов в системе.
    Полезен при изменении параметров обработки или обновлении документов.
    
    ## ⚠️ Внимание
    
    **Это операция удаляет все существующие данные и создает новые индексы!**
    
    ## 🔄 Процесс переиндексации
    
    1. **Очистка**: Удаление всех существующих документов из хранилища
    2. **Загрузка**: Чтение документов из исходной директории
    3. **Разделение**: Разбиение на чанки с новыми параметрами
    4. **Индексация**: Создание новых векторных представлений
    5. **Сохранение**: Запись в базу данных
    
    ## 🎯 Применение
    
    - Изменение параметров `chunk_size` или `chunk_overlap`
    - Обновление embedding модели
    - Исправление проблем с индексацией
    - Полная перестройка базы знаний
    
    ## 📝 Пример использования
    
    ```bash
    curl -X POST "http://localhost:8000/api/reindex"
    ```
    
    ## ⏱️ Время выполнения
    
    Время зависит от количества документов и их размера.
    Для больших коллекций может занять несколько минут.
    """,
    responses={
        200: {
            "description": "Переиндексация завершена успешно",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Документы успешно переиндексированы",
                        "documents_count": 10,
                        "chunks_count": 50,
                        "semantic_chunks": 40,
                        "fallback_chunks": 10
                    }
                }
            }
        },
        503: {
            "description": "RAG система не инициализирована",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RAG система не инициализирована"
                    }
                }
            }
        },
        500: {
            "description": "Ошибка переиндексации",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Ошибка при переиндексации документов: Не удалось подключиться к базе данных"
                    }
                }
            }
        }
    },
    tags=["Управление документами"]
)
async def reindex_endpoint():
    """
    Endpoint для полной переиндексации документов
    
    Удаляет все существующие документы из векторного хранилища
    и создает новые индексы с текущими параметрами обработки.
    
    Returns:
        IngestResponse: Результат переиндексации с статистикой
        
    Raises:
        HTTPException: При ошибках переиндексации
    """
    global rag_system
    
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG система не инициализирована"
        )
    
    try:
        # Очищаем существующие данные
        from main import VectorStoreManager
        manager = VectorStoreManager(rag_system)
        await manager.clear_collection()
        
        # Загружаем документы заново
        documents_dir = "/app/documents"
        if not os.path.exists(documents_dir):
            documents_dir = "./documents"
            
        documents = rag_system.load_documents(documents_dir)
        
        if not documents:
            return {
                "message": "Документы не найдены для переиндексации",
                "documents_processed": 0,
                "chunks_created": 0
            }
        
        # Разделяем на чанки с новыми настройками
        split_docs = rag_system.split_documents(
            documents, 
            chunk_size=CHUNK_SIZE, 
            chunk_overlap=CHUNK_OVERLAP
        )
        
        # Добавляем в векторное хранилище
        await rag_system.add_documents_to_vector_store(split_docs)
        
        # Пересоздаем ретривер с дедупликацией
        rag_system.create_retriever(
            search_type="similarity", 
            k=SIMILARITY_SEARCH_K
        )
        
        return IngestResponse(
            message="Документы успешно переиндексированы",
            documents_count=len(documents),
            chunks_count=len(split_docs),
            semantic_chunks=len([d for d in split_docs if d.metadata.get('chunk_type') == 'semantic']),
            fallback_chunks=len([d for d in split_docs if d.metadata.get('chunk_type') == 'fallback'])
        )
        
    except Exception as e:
        logger.error(f"Ошибка при переиндексации документов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при переиндексации документов: {str(e)}"
        )

# Дополнительные utility endpoints
@app.get(
    "/",
    summary="Корневой endpoint",
    description="""
    ## 🏠 Добро пожаловать в RAG System API
    
    Это корневой endpoint API системы Retrieval-Augmented Generation.
    
    ## 🔗 Полезные ссылки
    
    - **Документация**: `/docs` - Swagger UI
    - **ReDoc**: `/redoc` - Альтернативная документация
    - **OpenAPI**: `/openapi.json` - Спецификация API
    - **Health Check**: `/health` - Состояние системы
    - **Статистика**: `/api/stats` - Статистика хранилища
    
    ## 🚀 Быстрый старт
    
    1. Проверьте состояние системы: `GET /health`
    2. Отправьте запрос: `POST /api/query`
    3. Изучите документацию: `GET /docs`
    """,
    responses={
        200: {
            "description": "Информация о API",
            "content": {
                "application/json": {
                    "example": {
                        "message": "RAG System API",
                        "version": "1.0.0",
                        "status": "running",
                        "docs_url": "/docs",
                        "health_url": "/health"
                    }
                }
            }
        }
    },
    tags=["Информация"]
)
async def root():
    """
    Корневой endpoint API
    
    Предоставляет базовую информацию о системе и ссылки на документацию.
    
    Returns:
        dict: Информация о API и полезные ссылки
    """
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "health_url": "/health",
        "description": "Система поиска с дополненной генерацией"
    }

@app.get(
    "/api/info",
    response_model=SystemInfoResponse,
    summary="Информация о конфигурации системы",
    description="""
    ## ⚙️ Информация о конфигурации системы
    
    Этот endpoint предоставляет детальную информацию о текущей конфигурации
    RAG системы, включая модели, параметры и статус инициализации.
    
    ## 📊 Параметры конфигурации
    
    - **embedding_model**: Модель для создания векторных представлений
    - **llm_model**: Языковая модель для генерации ответов
    - **collection_name**: Название коллекции в векторном хранилище
    - **chunk_size**: Размер чанка для разделения документов
    - **chunk_overlap**: Перекрытие между чанками
    - **similarity_search_k**: Количество результатов поиска
    - **system_initialized**: Статус инициализации системы
    
    ## 🔍 Использование
    
    Полезно для:
    - Проверки текущих настроек
    - Диагностики конфигурации
    - Отладки проблем
    - Мониторинга состояния
    
    ## 📝 Пример ответа
    
    ```json
    {
      "embedding_model": "intfloat/e5-base-v2",
      "llm_model": "mistral-small",
      "collection_name": "rag_collection",
      "chunk_size": 512,
      "chunk_overlap": 64,
      "similarity_search_k": 5,
              "system_initialized": True
    }
    ```
    """,
    responses={
        200: {
            "description": "Информация о системе получена",
            "content": {
                "application/json": {
                    "example": {
                        "embedding_model": "intfloat/e5-base-v2",
                        "llm_model": "mistral-small",
                        "collection_name": "rag_collection",
                        "chunk_size": 512,
                        "chunk_overlap": 64,
                        "similarity_search_k": 5,
                        "system_initialized": True
                    }
                }
            }
        }
    },
    tags=["Информация"]
)
async def info_endpoint():
    """
    Информация о конфигурации системы
    
    Возвращает детальную информацию о текущих настройках
    и состоянии инициализации RAG системы.
    
    Returns:
        SystemInfoResponse: Информация о конфигурации системы
    """
    global rag_system
    
    return SystemInfoResponse(
        embedding_model=EMBEDDING_MODEL_NAME,
        llm_model=LLM_MODEL_NAME,
        collection_name=VECTOR_STORE_COLLECTION_NAME,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        similarity_search_k=SIMILARITY_SEARCH_K,
        system_initialized=rag_system is not None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=APP_PORT,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )