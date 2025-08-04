#!/usr/bin/env python3
"""
CLI скрипт для индексации документов в RAG системе
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Добавляем путь к модулям приложения
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.rag_system import RAGSystem
from app.document_processor import load_docx_files, get_document_stats

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Индексация документов для RAG системы"
    )
    parser.add_argument(
        "--docs-path",
        type=str,
        default=settings.docs_path,
        help="Путь к папке с документами"
    )
    parser.add_argument(
        "--index-path",
        type=str,
        default=settings.index_path,
        help="Путь для сохранения FAISS индекса"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=settings.chunk_size,
        help="Размер чанка в символах"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=settings.chunk_overlap,
        help="Перекрытие между чанками"
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=settings.embedding_model_name,
        help="Модель эмбеддингов"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Принудительная переиндексация"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Подробный вывод"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logger.info("Начало индексации документов...")
        logger.info(f"Путь к документам: {args.docs_path}")
        logger.info(f"Путь к индексу: {args.index_path}")
        logger.info(f"Модель эмбеддингов: {args.embedding_model}")
        logger.info(f"Размер чанка: {args.chunk_size}")
        logger.info(f"Перекрытие чанков: {args.chunk_overlap}")
        
        # Проверка существования папки с документами
        docs_path = Path(args.docs_path)
        if not docs_path.exists():
            logger.error(f"Папка с документами не найдена: {args.docs_path}")
            sys.exit(1)
        
        # Загрузка документов
        logger.info("Загрузка документов...")
        documents = load_docx_files(args.docs_path)
        
        if not documents:
            logger.error("Документы не найдены")
            sys.exit(1)
        
        # Вывод статистики документов
        stats = get_document_stats(documents)
        logger.info(f"Найдено документов: {stats['total_documents']}")
        logger.info(f"Общий размер: {stats['total_size_bytes'] / 1024:.2f} KB")
        logger.info(f"Общее количество символов: {stats['total_characters']}")
        
        # Создание RAG системы
        logger.info("Инициализация RAG системы...")
        rag = RAGSystem()
        
        # Временное изменение настроек
        original_docs_path = settings.docs_path
        original_index_path = settings.index_path
        original_chunk_size = settings.chunk_size
        original_chunk_overlap = settings.chunk_overlap
        original_embedding_model = settings.embedding_model_name
        
        settings.docs_path = args.docs_path
        settings.index_path = args.index_path
        settings.chunk_size = args.chunk_size
        settings.chunk_overlap = args.chunk_overlap
        settings.embedding_model_name = args.embedding_model
        
        try:
            # Инициализация системы
            rag.initialize()
            
            # Получение финальной статистики
            final_stats = rag.get_stats()
            
            logger.info("Индексация завершена успешно!")
            logger.info(f"Обработано документов: {final_stats['total_documents']}")
            logger.info(f"Создано чанков: {final_stats['total_chunks']}")
            logger.info(f"Размер индекса: {final_stats['index_size_mb']:.2f} MB")
            logger.info(f"Последнее обновление: {final_stats['last_updated']}")
            
        finally:
            # Восстановление оригинальных настроек
            settings.docs_path = original_docs_path
            settings.index_path = original_index_path
            settings.chunk_size = original_chunk_size
            settings.chunk_overlap = original_chunk_overlap
            settings.embedding_model_name = original_embedding_model
        
    except KeyboardInterrupt:
        logger.info("Индексация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка при индексации: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 