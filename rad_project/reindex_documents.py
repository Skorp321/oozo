#!/usr/bin/env python3
"""
Скрипт для переиндексации документов с улучшенным семантическим разделением на чанки
"""

import asyncio
import logging
from main import RAGSystem
from config.settings import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reindex_documents():
    """Переиндексация документов с новыми настройками"""
    
    # Настройки подключения к базе данных
    DB_CONNECTION_STRING = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    
    # Создание экземпляра RAG системы
    rag = RAGSystem(
        db_connection_string=DB_CONNECTION_STRING,
        collection_name=VECTOR_STORE_COLLECTION_NAME
    )
    
    try:
        logger.info("Начинаем переиндексацию документов...")
        
        # 1. Настройка базы данных
        await rag.setup_database()
        logger.info("База данных настроена")
        
        # 2. Инициализация векторного хранилища
        rag.initialize_vector_store()
        logger.info("Векторное хранилище инициализировано")
        
        # 3. Очистка существующих данных
        from main import VectorStoreManager
        manager = VectorStoreManager(rag)
        await manager.clear_collection()
        logger.info("Существующие данные очищены")
        
        # 4. Загрузка документов
        documents_dir = "/app/documents"
        if not os.path.exists(documents_dir):
            documents_dir = "./documents"  # Fallback для локальной разработки
            
        documents = rag.load_documents(documents_dir)
        logger.info(f"Загружено {len(documents)} документов")
        
        if documents:
            # 5. Разделение документов на чанки с новыми настройками
            split_docs = rag.split_documents(
                documents, 
                chunk_size=CHUNK_SIZE, 
                chunk_overlap=CHUNK_OVERLAP
            )
            logger.info(f"Документы разделены на {len(split_docs)} чанков")
            
            # 6. Добавление документов в векторное хранилище
            await rag.add_documents_to_vector_store(split_docs)
            logger.info("Документы добавлены в векторное хранилище")
            
            # 7. Создание ретривера с дедупликацией
            rag.create_retriever(
                search_type="similarity", 
                k=SIMILARITY_SEARCH_K
            )
            logger.info("Ретривер с дедупликацией создан")
            
            # 8. Создание QA цепочки
            custom_prompt = """
            Ты - полезный ассистент. Используй предоставленный контекст для ответа на вопрос.
            Отвечай точно и по существу на русском языке. Если информации недостаточно, скажи об этом.
            
            Контекст: {context}
            
            Вопрос: {question}
            
            Подробный ответ:
            """
            rag.create_qa_chain(custom_prompt)
            logger.info("QA цепочка создана")
            
            # 9. Получение статистики
            stats = await manager.get_collection_stats()
            logger.info(f"Статистика коллекции: {stats}")
            
            # 10. Тестовый запрос
            test_query = "какой предмет договора?"
            logger.info(f"Тестируем запрос: '{test_query}'")
            
            try:
                # Тест прямого поиска
                similar_docs = await rag.similarity_search(test_query, k=5)
                logger.info(f"Найдено {len(similar_docs)} уникальных документов")
                
                for i, doc in enumerate(similar_docs, 1):
                    logger.info(f"Документ {i}:")
                    logger.info(f"  Заголовок: {doc.metadata.get('chunk_title', 'N/A')}")
                    logger.info(f"  Раздел: {doc.metadata.get('section_number', 'N/A')}")
                    logger.info(f"  Тип чанка: {doc.metadata.get('chunk_type', 'N/A')}")
                    logger.info(f"  Содержимое: {doc.page_content[:200]}...")
                    logger.info("---")
                
                # Тест QA цепочки
                result = await rag.query(test_query, return_sources=True)
                logger.info(f"Ответ QA: {result['answer'][:200]}...")
                logger.info(f"Количество источников: {len(result.get('sources', []))}")
                
            except Exception as e:
                logger.error(f"Ошибка при тестировании: {e}")
        
        else:
            logger.warning("Документы не найдены для загрузки")
            
    except Exception as e:
        logger.error(f"Ошибка при переиндексации: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(reindex_documents()) 