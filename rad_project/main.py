import os
import asyncio
from typing import List, Optional
import asyncpg
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import PGVector
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.schema import BaseRetriever
import logging
from config.settings import *
from config.settings import EMBEDDING_FALLBACK_MODEL
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mistralai.chat_models import ChatMistralAI
from utils.document_chunker import DocumentChunker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(
        self,
        db_connection_string: str,
        collection_name: str = "documents",
        embedding_model: str = "intfloat/e5-base-v2",
        llm_model: str = "mistral-small"
    ):
        """
        Инициализация RAG системы
        
        Args:
            db_connection_string: строка подключения к PostgreSQL
            collection_name: имя коллекции для хранения векторов
            embedding_model: модель для создания эмбеддингов
            llm_model: языковая модель для генерации ответов
        """
        self.db_connection_string = db_connection_string
        self.collection_name = collection_name
        
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={"device": EMBEDDING_DEVICE},
                cache_folder="/app/models",  # Кэширование моделей
                encode_kwargs={"batch_size": 8}  # Уменьшенный batch size
            )
        except Exception as e:
            logger.warning(f"Ошибка загрузки модели эмбеддингов: {e}")
            logger.info("Пробуем загрузить модель с увеличенным таймаутом...")
            try:
                import os
                os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '300'  # 5 минут таймаут
                os.environ['TRANSFORMERS_CACHE'] = '/app/models'
                
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL_NAME,
                    model_kwargs={"device": EMBEDDING_DEVICE},
                    cache_folder="/app/models",
                    encode_kwargs={"batch_size": 4}
                )
            except Exception as e2:
                logger.warning(f"Не удалось загрузить основную модель: {e2}")
                logger.info("Пробуем загрузить fallback модель...")
                try:
                    self.embeddings = HuggingFaceEmbeddings(
                        model_name=EMBEDDING_FALLBACK_MODEL,
                        model_kwargs={"device": EMBEDDING_DEVICE},
                        cache_folder="/app/models",
                        encode_kwargs={"batch_size": 2}
                    )
                    logger.info(f"Загружена fallback модель: {EMBEDDING_FALLBACK_MODEL}")
                except Exception as e3:
                    raise RuntimeError(f"Не удалось загрузить ни основную, ни fallback модель эмбеддингов: {e3}")
        try:
            self.llm = ChatMistralAI(
                api_key=MISTRAL_API_KEY or LLM_API_KEY,
                model=llm_model,
                temperature=LLM_TEMPERATURE
            )
        except Exception as e:
            raise RuntimeError(f"Ошибка инициализации Mistral LLM: {e}")
        
        # Инициализация векторного хранилища
        self.vector_store = None
        self.retriever = None
        self.qa_chain = None
        
    async def setup_database(self):
        """Настройка базы данных PostgreSQL с расширением pgvector"""
        conn = await asyncpg.connect(self.db_connection_string)
        try:
            # Создание расширения pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("Расширение pgvector создано или уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании расширения pgvector: {e}")
        finally:
            await conn.close()
    
    def initialize_vector_store(self):
        """Инициализация векторного хранилища PGVector"""
        self.vector_store = PGVector(
            connection_string=self.db_connection_string,
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
        )
        logger.info(f"Векторное хранилище инициализировано для коллекции: {self.collection_name}")
    
    def load_documents(self, directory_path: str, file_extensions: List[str] = [".txt", ".md"]) -> List[Document]:
        """
        Загрузка документов из директории
        
        Args:
            directory_path: путь к директории с документами
            file_extensions: список расширений файлов для загрузки
            
        Returns:
            Список документов LangChain
        """
        documents = []
        
        for ext in file_extensions:
            loader = DirectoryLoader(
                directory_path,
                glob=f"**/*{ext}",
                loader_cls=TextLoader
            )
            docs = loader.load()
            documents.extend(docs)
        
        logger.info(f"Загружено {len(documents)} документов")
        return documents
    
    def split_documents(self, documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
        """
        Разделение документов на чанки с использованием семантического анализа
        
        Args:
            documents: список документов
            chunk_size: размер чанка (используется как fallback)
            chunk_overlap: перекрытие между чанками (используется как fallback)
            
        Returns:
            Список разделенных документов
        """
        split_docs = []
        chunker = DocumentChunker()
        
        for doc in documents:
            try:
                # Пытаемся использовать семантическое разделение
                if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                    file_path = doc.metadata['source']
                    if os.path.exists(file_path):
                        # Используем DocumentChunker для структурированных документов
                        chunks = chunker.chunk_document(file_path)
                        
                        for chunk in chunks:
                            # Создаем Document объект для каждого чанка
                            chunk_doc = Document(
                                page_content=chunk['content'],
                                metadata={
                                    **doc.metadata,
                                    'chunk_title': chunk['title'],
                                    'section_number': chunk['section_number'],
                                    'hierarchy_path': ' → '.join([s['title'] for s in chunk['hierarchy_path']]) if chunk['hierarchy_path'] else '',
                                    'chunk_type': 'semantic'
                                }
                            )
                            split_docs.append(chunk_doc)
                        continue
                
                # Fallback на RecursiveCharacterTextSplitter для неструктурированных документов
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len,
                )
                
                fallback_docs = text_splitter.split_documents([doc])
                for fallback_doc in fallback_docs:
                    fallback_doc.metadata['chunk_type'] = 'fallback'
                split_docs.extend(fallback_docs)
                
            except Exception as e:
                logger.warning(f"Ошибка при разделении документа {doc.metadata.get('source', 'unknown')}: {e}")
                # Fallback на простой splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len,
                )
                fallback_docs = text_splitter.split_documents([doc])
                for fallback_doc in fallback_docs:
                    fallback_doc.metadata['chunk_type'] = 'fallback'
                split_docs.extend(fallback_docs)
        
        logger.info(f"Документы разделены на {len(split_docs)} чанков (семантических: {len([d for d in split_docs if d.metadata.get('chunk_type') == 'semantic'])})")
        return split_docs
    
    async def add_documents_to_vector_store(self, documents: List[Document]):
        """
        Добавление документов в векторное хранилище
        
        Args:
            documents: список документов для добавления
        """
        if not self.vector_store:
            raise ValueError("Векторное хранилище не инициализировано")
        
        # Добавление документов в батчах для оптимизации
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            await self.vector_store.aadd_documents(batch)
            logger.info(f"Добавлен батч {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
        
        logger.info(f"Все {len(documents)} документов добавлены в векторное хранилище")
    
    def create_retriever(self, search_type: str = "similarity", k: int = 4, score_threshold: float = 0.7):
        """
        Создание ретривера для поиска релевантных документов с дедупликацией
        
        Args:
            search_type: тип поиска ('similarity' или 'similarity_score_threshold')
            k: количество возвращаемых документов
            score_threshold: порог схожести для фильтрации результатов
        """
        if not self.vector_store:
            raise ValueError("Векторное хранилище не инициализировано")
        
        # Используем стандартный ретривер с увеличенным k для дедупликации
        search_k = min(k * 3, 20)  # Получаем в 3 раза больше для фильтрации
        
        if search_type == "similarity_score_threshold":
            self.retriever = self.vector_store.as_retriever(
                search_type=search_type,
                search_kwargs={"score_threshold": score_threshold, "k": search_k}
            )
        else:
            self.retriever = self.vector_store.as_retriever(
                search_type=search_type,
                search_kwargs={"k": search_k}
            )
        
        logger.info(f"Ретривер с дедупликацией создан: тип={search_type}, k={k}")
    
    def create_qa_chain(self, custom_prompt: Optional[str] = None):
        """
        Создание QA цепочки для генерации ответов
        
        Args:
            custom_prompt: кастомный промпт для генерации ответов
        """
        if not self.retriever:
            raise ValueError("Ретривер не создан")
        
        # Дефолтный промпт
        default_prompt = """
        Используй следующий контекст для ответа на вопрос. 
        Если ты не знаешь ответа, просто скажи, что не знаешь, не пытайся придумать ответ.
        
        Контекст: {context}
        
        Вопрос: {question}
        
        Ответ:
        """
        
        prompt_template = PromptTemplate(
            template=custom_prompt or default_prompt,
            input_variables=["context", "question"]
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            chain_type_kwargs={"prompt": prompt_template},
            return_source_documents=True
        )
        
        logger.info("QA цепочка создана")
    
    async def query(self, question: str, return_sources: bool = True) -> dict:
        """
        Выполнение запроса к RAG системе с дедупликацией источников
        
        Args:
            question: вопрос пользователя
            return_sources: возвращать ли источники
            
        Returns:
            Словарь с результатом и источниками
        """
        if not self.qa_chain:
            raise ValueError("QA цепочка не создана")
        
        result = await self.qa_chain.ainvoke({"query": question})
        
        response = {
            "answer": result["result"],
            "question": question
        }
        
        if return_sources and "source_documents" in result:
            # Дедупликация источников
            unique_sources = []
            seen_contents = set()
            seen_sections = set()
            
            for doc in result["source_documents"]:
                # Нормализуем содержимое для сравнения
                normalized_content = doc.page_content.strip()[:100]
                
                # Проверяем уникальность по содержимому и разделу
                section_key = doc.metadata.get('section_number', '') + doc.metadata.get('chunk_title', '')
                
                if normalized_content not in seen_contents and section_key not in seen_sections:
                    seen_contents.add(normalized_content)
                    seen_sections.add(section_key)
                    unique_sources.append({
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "metadata": doc.metadata
                    })
            
            response["sources"] = unique_sources
            logger.info(f"Найдено {len(unique_sources)} уникальных источников из {len(result['source_documents'])} кандидатов")
        
        return response
    
    async def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Прямой поиск по схожести в векторном хранилище с дедупликацией
        
        Args:
            query: поисковый запрос
            k: количество результатов
            
        Returns:
            Список релевантных документов
        """
        if not self.vector_store:
            raise ValueError("Векторное хранилище не инициализировано")
        
        # Получаем больше документов для лучшей дедупликации
        search_k = min(k * 3, 20)
        docs_with_scores = await self.vector_store.asimilarity_search_with_score(query, k=search_k)
        
        # Дедупликация по содержимому и метаданным
        unique_docs = []
        seen_contents = set()
        seen_sections = set()
        
        for doc, score in docs_with_scores:
            # Нормализуем содержимое для сравнения
            normalized_content = doc.page_content.strip()[:100]  # Первые 100 символов
            
            # Проверяем уникальность по содержимому и разделу
            section_key = doc.metadata.get('section_number', '') + doc.metadata.get('chunk_title', '')
            
            if normalized_content not in seen_contents and section_key not in seen_sections:
                seen_contents.add(normalized_content)
                seen_sections.add(section_key)
                unique_docs.append(doc)
                
                if len(unique_docs) >= k:
                    break
        
        logger.info(f"Найдено {len(unique_docs)} уникальных документов из {len(docs_with_scores)} кандидатов")
        return unique_docs


def health_check():
    """
    Расширенная проверка состояния системы с детальной диагностикой
    """
    health_status = {
        "status": "ok",
        "components": {},
        "issues": [],
        "recommendations": []
    }
    
    # 1. Проверка API ключа Mistral
    try:
        mistral_key = MISTRAL_API_KEY or LLM_API_KEY
        if not mistral_key or mistral_key.strip() == "" or mistral_key == "your_actual_mistral_api_key_here":
            health_status["components"]["mistral_api_key"] = "missing"
            health_status["issues"].append("MISTRAL_API_KEY не настроен или содержит placeholder значение")
            health_status["recommendations"].append("Получите API ключ на https://console.mistral.ai/ и установите переменную MISTRAL_API_KEY")
        else:
            # Пытаемся создать ChatMistralAI объект для проверки ключа
            try:
                from langchain_mistralai.chat_models import ChatMistralAI
                test_llm = ChatMistralAI(
                    api_key=mistral_key,
                    model=LLM_MODEL_NAME,
                    temperature=LLM_TEMPERATURE
                )
                health_status["components"]["mistral_api_key"] = "valid"
            except Exception as e:
                health_status["components"]["mistral_api_key"] = "invalid"
                health_status["issues"].append(f"Ошибка инициализации Mistral LLM: {str(e)}")
                health_status["recommendations"].append("Проверьте корректность MISTRAL_API_KEY")
    except Exception as e:
        health_status["components"]["mistral_api_key"] = "error"
        health_status["issues"].append(f"Ошибка проверки Mistral API ключа: {str(e)}")
    
    # 2. Проверка моделей эмбеддингов
    try:
        _ = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME, 
            model_kwargs={"device": EMBEDDING_DEVICE},
            cache_folder="/app/models"
        )
        health_status["components"]["embedding_model"] = "loaded"
    except Exception as e:
        health_status["components"]["embedding_model"] = "error"
        health_status["issues"].append(f"Ошибка загрузки модели эмбеддингов: {str(e)}")
        health_status["recommendations"].append("Проверьте доступность интернета и корректность названия модели")
        
        # Пытаемся fallback модель
        try:
            _ = HuggingFaceEmbeddings(
                model_name=EMBEDDING_FALLBACK_MODEL,
                model_kwargs={"device": EMBEDDING_DEVICE},
                cache_folder="/app/models"
            )
            health_status["components"]["embedding_fallback"] = "loaded"
            health_status["recommendations"].append(f"Используется fallback модель: {EMBEDDING_FALLBACK_MODEL}")
        except Exception as e2:
            health_status["components"]["embedding_fallback"] = "error"
            health_status["issues"].append(f"Fallback модель также недоступна: {str(e2)}")
    
    # 3. Проверка подключения к базе данных (упрощенная проверка без asyncio)
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Парсим DATABASE_URL для получения параметров подключения
        parsed = urlparse(DATABASE_URL)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # убираем первый слэш
            user=parsed.username,
            password=parsed.password
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        health_status["components"]["database"] = "connected"
            
    except ImportError:
        health_status["components"]["database"] = "warning"
        health_status["issues"].append("psycopg2 не найден - используется asyncpg")
        health_status["recommendations"].append("Проверка БД будет выполнена при запросах")
    except Exception as e:
        health_status["components"]["database"] = "error"
        health_status["issues"].append(f"Ошибка подключения к базе данных: {str(e)}")
        health_status["recommendations"].append("Проверьте работу PostgreSQL контейнера: docker compose ps postgres-pgvector")
    
    # 4. Проверка переменных окружения
    critical_vars = {
        "DATABASE_URL": DATABASE_URL,
        "EMBEDDING_MODEL_NAME": EMBEDDING_MODEL_NAME,
        "LLM_MODEL_NAME": LLM_MODEL_NAME
    }
    
    missing_vars = []
    for var_name, var_value in critical_vars.items():
        if not var_value or var_value.strip() == "":
            missing_vars.append(var_name)
    
    if missing_vars:
        health_status["components"]["environment"] = "incomplete"
        health_status["issues"].append(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        health_status["recommendations"].append("Создайте файл .env с необходимыми переменными")
    else:
        health_status["components"]["environment"] = "complete"
    
    # Определяем общий статус
    if health_status["issues"]:
        health_status["status"] = "degraded" if health_status["components"].get("database") == "connected" else "error"
        
        # Приоритетные проблемы
        if health_status["components"].get("mistral_api_key") in ["missing", "invalid"]:
            health_status["priority_issue"] = "MISTRAL_API_KEY"
            health_status["status"] = "error"
    
    return health_status


# Пример использования RAG системы (для демонстрации)
async def demo_main():
    """
    Демонстрационная функция для тестирования RAG системы
    Эта функция больше не используется в продакшене, так как RAG система
    теперь обернута в FastAPI (см. api.py)
    """
    # Настройки подключения к базе данных
    DB_CONNECTION_STRING = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    
    # Создание экземпляра RAG системы
    rag = RAGSystem(
        db_connection_string=DB_CONNECTION_STRING,
        collection_name=VECTOR_STORE_COLLECTION_NAME
    )
    
    try:
        # 1. Настройка базы данных
        await rag.setup_database()
        
        # 2. Инициализация векторного хранилища
        rag.initialize_vector_store()
        
        # 3. Загрузка документов
        documents = rag.load_documents("./documents")
        
        # 4. Разделение документов на чанки
        split_docs = rag.split_documents(documents, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        
        # 5. Добавление документов в векторное хранилище
        await rag.add_documents_to_vector_store(split_docs)
        
        # 6. Создание ретривера
        rag.create_retriever(search_type="similarity", k=SIMILARITY_SEARCH_K)
        
        # 7. Создание QA цепочки
        custom_prompt = """
        Ты - полезный ассистент. Используй предоставленный контекст для ответа на вопрос.
        Отвечай точно и по существу. Если информации недостаточно, скажи об этом.
        
        Контекст: {context}
        
        Вопрос: {question}
        
        Подробный ответ:
        """
        rag.create_qa_chain(custom_prompt)
        
        # 8. Примеры запросов
        questions = [
            "Что такое машинное обучение?",
            "Как работают нейронные сети?",
            "Расскажи о методах обработки естественного языка"
        ]
        
        for question in questions:
            print(f"\n{'='*50}")
            print(f"Вопрос: {question}")
            print(f"{'='*50}")
            
            result = await rag.query(question)
            print(f"Ответ: {result['answer']}")
            
            if 'sources' in result:
                print(f"\nИсточники:")
                for i, source in enumerate(result['sources'], 1):
                    print(f"{i}. {source['content']}")
                    print(f"   Метаданные: {source['metadata']}")
    
    except Exception as e:
        logger.error(f"Ошибка в работе RAG системы: {e}")


# Дополнительные утилиты для управления векторным хранилищем
class VectorStoreManager:
    def __init__(self, rag_system: RAGSystem):
        self.rag = rag_system
    
    async def clear_collection(self):
        """Очистка коллекции"""
        if self.rag.vector_store:
            # Прямое выполнение SQL для очистки таблицы
            conn = await asyncpg.connect(self.rag.db_connection_string)
            try:
                await conn.execute(f"DELETE FROM langchain_pg_embedding WHERE collection_id IN (SELECT uuid FROM langchain_pg_collection WHERE name = '{self.rag.collection_name}');")
                await conn.execute(f"DELETE FROM langchain_pg_collection WHERE name = '{self.rag.collection_name}';")
                logger.info(f"Коллекция {self.rag.collection_name} очищена")
            finally:
                await conn.close()
    
    async def get_collection_stats(self) -> dict:
        """Получение статистики коллекции"""
        conn = await asyncpg.connect(self.rag.db_connection_string)
        try:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as document_count,
                    pg_size_pretty(pg_total_relation_size('langchain_pg_embedding')) as table_size
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = $1
            """, self.rag.collection_name)
            
            return {
                "document_count": stats["document_count"] if stats else 0,
                "table_size": stats["table_size"] if stats else "0 bytes"
            }
        finally:
            await conn.close()


if __name__ == "__main__":
    # Запуск демонстрационной функции (только для тестирования)
    # В продакшене используется FastAPI сервер (api.py)
    asyncio.run(demo_main())