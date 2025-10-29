import os
import logging
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from datetime import datetime

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel

from .config import settings
from .document_processor import load_docx_files, split_documents, get_document_stats
from .database import get_db_session
from .models import Chunk

logger = logging.getLogger(__name__)

def format_documents(documents: list[Document]):
    return "\n\n".join(doc.page_content for doc in documents)

def format_answer(response: str):
    return response.content.split('</think>')[-1].strip()
        
        
class RAGSystem:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.llm = None
        self.documents = []
        self.stats = {}
        self._initialized = False
    
    def initialize(self):
        """
        Инициализация RAG системы
        """
        try:
            logger.info("Инициализация RAG системы...")
            
            # Создание модели эмбеддингов
            self._create_embeddings()
            
            # Загрузка или создание векторного хранилища
            self._load_or_create_vector_store()
            
            # Настройка QA цепочки
            self._init_llm()
            
            self._initialized = True
            logger.info("RAG система успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации RAG системы: {e}")
            raise
    
    def _create_embeddings(self):
        """
        Создание модели эмбеддингов
        """
        try:
            logger.info(f"Загрузка модели эмбеддингов: {settings.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.embedding_model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("Модель эмбеддингов загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели эмбеддингов: {e}")
            raise
    
    def _load_or_create_vector_store(self):
        """
        Загрузка существующего или создание нового векторного хранилища
        """
        index_path = Path(settings.index_path)
        
        logger.info(f"Проверка FAISS индекса по пути: {index_path}")
        logger.info(f"Абсолютный путь: {index_path.absolute()}")
        
        # Проверка существования директории
        if not index_path.exists():
            logger.info(f"Директория индекса не существует: {index_path}")
        else:
            logger.info(f"Директория индекса существует: {index_path}")
            # Проверка содержимого директории
            try:
                files = list(index_path.iterdir())
                logger.info(f"Файлы в директории индекса: {[f.name for f in files]}")
            except PermissionError:
                logger.error(f"Нет прав доступа к директории: {index_path}")
            except Exception as e:
                logger.error(f"Ошибка при чтении директории: {e}")
        
        # Проверка существования файлов индекса
        index_file = index_path / "index.faiss"
        pkl_file = index_path / "index.pkl"
        metadata_file = index_path / "metadata.pkl"
        
        required_files = [index_file, pkl_file]
        existing_files = [f for f in required_files if f.exists()]
        
        logger.info(f"Требуемые файлы: {[f.name for f in required_files]}")
        logger.info(f"Существующие файлы: {[f.name for f in existing_files]}")
        
        if len(existing_files) == len(required_files):
            try:
                logger.info("Загрузка существующего FAISS индекса...")
                
                # Проверка размера файлов
                for file_path in existing_files:
                    if file_path.exists():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        logger.info(f"Файл {file_path.name}: {size_mb:.2f} MB")
                
                self.vector_store = FAISS.load_local(
                    str(index_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                
                # Загрузка метаданных
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'rb') as f:
                            self.stats = pickle.load(f)
                        logger.info(f"Метаданные загружены: {self.stats}")
                    except Exception as e:
                        logger.warning(f"Ошибка при загрузке метаданных: {e}")
                        self.stats = {}
                else:
                    logger.info("Файл метаданных не найден, создание пустых метаданных")
                    self.stats = {}
                
                logger.info(f"FAISS индекс загружен успешно: {self.vector_store.index.ntotal} векторов")
                
                # Загрузка документов для создания BM25 ретривера
                self.documents = load_docx_files(settings.docs_path)
                if self.documents:
                    chunks = split_documents(self.documents)
                    if chunks:
                        # Создание гибридного ретривера
                        bm25 = BM25Retriever.from_documents(chunks)
                        self.retriever = EnsembleRetriever(
                            retrievers=[bm25, self.vector_store.as_retriever(search_kwargs={"k": 5})],
                            weights=[0.5, 0.5]
                        )
                        logger.info("Гибридный ретривер создан")
                    else:
                        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
                        logger.info("Создан простой векторный ретривер")
                else:
                    self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
                    logger.info("Документы не найдены, создан простой векторный ретривер")
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке FAISS индекса: {e}")
                logger.info("Создание нового индекса...")
                self._build_vector_store()
        else:
            logger.info(f"FAISS индекс не найден (найдено {len(existing_files)} из {len(required_files)} файлов), создание нового...")
            self._build_vector_store()
    
    def _build_vector_store(self):
        """
        Создание векторного хранилища из документов
        """
        try:
            # Загрузка документов
            self.documents = load_docx_files(settings.docs_path)
            
            if not self.documents:
                logger.warning("Документы не найдены, создание пустого индекса")
                # Создаем пустой индекс
                dummy_docs = [Document(page_content="", metadata={})]
                self.vector_store = FAISS.from_documents(dummy_docs, self.embeddings)
                # Не создаем retriever для пустых документов
                self.retriever = None
                self.stats = {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "index_size_mb": 0,
                    "last_updated": datetime.now().isoformat()
                }
                return
            
            # Разбивка на чанки
            chunks = split_documents(self.documents)
            
            # Создание векторного хранилища
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            # Создание гибридного ретривера
            bm25 = BM25Retriever.from_documents(chunks)
            self.retriever = EnsembleRetriever(
                retrievers=[bm25, self.vector_store.as_retriever(search_kwargs={"k": 5})],
                weights=[0.5, 0.5]
            )
            
            # Сохранение индекса
            self._save_vector_store()
            
            # Обновление статистики
            self._update_stats(chunks)
            
            logger.info(f"Векторное хранилище создано: {len(chunks)} чанков")
            
        except Exception as e:
            logger.error(f"Ошибка при создании векторного хранилища: {e}")
            raise
    
    def _save_vector_store(self):
        """
        Сохранение векторного хранилища
        """
        try:
            index_path = Path(settings.index_path)
            logger.info(f"Сохранение векторного хранилища в: {index_path}")
            logger.info(f"Абсолютный путь: {index_path.absolute()}")
            
            # Создание директории если не существует
            index_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Директория создана/проверена: {index_path}")
            
            # Проверка прав доступа
            if not os.access(index_path, os.W_OK):
                logger.error(f"Нет прав на запись в директорию: {index_path}")
                raise PermissionError(f"Нет прав на запись в директорию: {index_path}")
            
            # Сохранение FAISS индекса
            self.vector_store.save_local(str(index_path))
            logger.info("FAISS индекс сохранен")
            
            # Проверка созданных файлов
            saved_files = list(index_path.iterdir())
            logger.info(f"Созданные файлы: {[f.name for f in saved_files]}")
            
            # Проверка размеров файлов
            for file_path in saved_files:
                if file_path.exists():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Файл {file_path.name}: {size_mb:.2f} MB")
            
            # Сохранение метаданных
            metadata_path = index_path / "metadata.pkl"
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.stats, f)
            
            logger.info(f"Метаданные сохранены: {metadata_path}")
            logger.info(f"Векторное хранилище успешно сохранено: {index_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении векторного хранилища: {e}")
            raise
    
    def _update_stats(self, chunks: List[Document]):
        """
        Обновление статистики
        """
        doc_stats = get_document_stats(self.documents)
        
        # Расчет размера индекса
        index_size_mb = 0
        if self.vector_store and hasattr(self.vector_store.index, 'ntotal'):
            # Примерная оценка размера индекса
            index_size_mb = (self.vector_store.index.ntotal * 768 * 4) / (1024 * 1024)  # 768 dims, float32
        
        self.stats = {
            "total_documents": doc_stats["total_documents"],
            "total_chunks": len(chunks),
            "index_size_mb": round(index_size_mb, 2),
            "last_updated": datetime.now().isoformat()
        }
    
    def _init_llm(self):
        """
        Настройка QA цепочки
        """
        # Создание языковой модели
        repo_id = "model-run-vekow-trunk"

        self.llm = ChatOpenAI(
                    openai_api_key="dummy_key",
                    openai_api_base="https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1",
                    model=repo_id,
                    temperature=0.1,
                    streaming=True,
                    timeout=600  # 10 minutes
                )      
    
    def query(self, question: str, return_sources: bool = True) -> Dict[str, Any]:
        """
        Выполнение запроса к RAG системе
        """
        
        # Создание промпта
        template = """Ты - помощник по юридическим вопросам. Используй следующие части контекста из юридических документов, чтобы дать точный и полезный ответ на вопрос пользователя.

        Важные правила:
        1. Отвечай только на основе предоставленного контекста
        2. Если в контексте нет информации для ответа, честно скажи об этом
        3. Не придумывай информацию, которой нет в контексте
        4. Давай четкие и структурированные ответы
        5. При необходимости цитируй соответствующие части контекста
        6. Отвечай на русском языке
        
        Контекст: {context}
        
        Вопрос: {question}
        
        Ответ:"""
            
        prompt = ChatPromptTemplate.from_template(template)
        
        if not self._initialized:
            raise RuntimeError("RAG система не инициализирована")
        
        try:
            logger.info(f"Обработка запроса: {question}")
            
            # Проверяем наличие retriever
            if self.retriever is None:
                logger.warning("Retriever не инициализирован, используем прямой поиск по векторному хранилищу")
                chunks = self.vector_store.similarity_search(question, k=5) if self.vector_store else []
            else:
                chunks = self.retriever.invoke(question)
            context = format_documents(chunks)
            
            # Формируем финальный промпт из шаблона
            final_prompt = template.format(context=context, question=question)
            
            chain = prompt | self.llm
            result = chain.invoke({"context": context, "question": question})
            
            result = format_answer(result)

            # Обработка результата от RetrievalQA
            answer = result if result else "Не удалось получить ответ"

            # Используем те же чанки для извлечения ID
            source_documents = chunks if isinstance(chunks, list) else self.vector_store.similarity_search(question, k=5)
            logger.info(f"Тип чанков {type(source_documents)}")
            logger.info(f"Найденные чанки: {len(source_documents) if isinstance(source_documents, list) else 'N/A'}")
            
            # Извлекаем ID чанков из метаданных
            chunk_ids = []
            if isinstance(source_documents, list):
                for doc in source_documents:
                    if hasattr(doc, 'metadata') and doc.metadata:
                        db_id = doc.metadata.get("db_id")
                        if db_id:
                            chunk_ids.append(db_id)
            
            # Формирование источников
            sources = []
            if return_sources and source_documents:
                # В новом API контекст может быть строкой или списком документов
                if isinstance(source_documents, str):
                    # Если контекст - это строка, создаем один источник
                    sources.append({
                        "title": "Контекст",
                        "content": source_documents,
                        "score": 1.0,
                        "metadata": {}
                    })
                elif isinstance(source_documents, list):
                    for doc in source_documents:
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            sources.append({
                                "title": doc.metadata.get("title", "Неизвестный источник"),
                                "content": doc.page_content,
                                "score": 1.0,
                                "metadata": doc.metadata
                            })
            
            logger.info(f"Запрос обработан, найдено источников: {len(sources)}, chunk_ids: {chunk_ids}")
            
            return {
                "answer": answer,
                "sources": sources,
                "final_prompt": final_prompt,
                "chunk_ids": chunk_ids
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            # Получаем chunk_ids даже при ошибке, если чанки были найдены
            chunk_ids = []
            try:
                if self.vector_store:
                    error_docs = self.vector_store.similarity_search(question, k=5)
                    if error_docs:
                        chunk_ids = self._get_chunk_ids_from_documents(error_docs)
            except Exception as e2:
                logger.warning(f"Не удалось получить chunk_ids при ошибке: {e2}")
            
            return {
                "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
                "sources": [],
                "final_prompt": None,
                "chunk_ids": chunk_ids
            }
    
    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск похожих документов
        """
        if not self._initialized or not self.vector_store:
            return []
        
        try:
            docs_and_scores = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            results = []
            for doc, score in docs_and_scores:
                results.append({
                    "title": doc.metadata.get("title", "Неизвестный источник"),
                    "content": doc.page_content,
                    "score": float(score),
                    "metadata": doc.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске похожих документов: {e}")
            return []
    
    def reindex_documents(self) -> Dict[str, Any]:
        """
        Переиндексация документов
        """
        try:
            logger.info("Начало переиндексации документов...")
            
            # Загрузка документов
            self.documents = load_docx_files(settings.docs_path)
            
            if not self.documents:
                return {
                    "message": "Документы не найдены",
                    "documents_processed": 0,
                    "chunks_created": 0,
                    "index_size_mb": 0
                }
            
            # Разбивка на чанки
            chunks = split_documents(self.documents)
            
            # Создание нового векторного хранилища
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            # Сохранение
            self._save_vector_store()
            
            # Обновление статистики
            self._update_stats(chunks)
            
            # Пересоздание QA цепочки
            self._setup_qa_chain()
            
            logger.info("Переиндексация завершена")
            
            return {
                "message": "Документы успешно переиндексированы",
                "documents_processed": len(self.documents),
                "chunks_created": len(chunks),
                "index_size_mb": self.stats["index_size_mb"]
            }
            
        except Exception as e:
            logger.error(f"Ошибка при переиндексации: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики системы
        """
        return self.stats.copy()


# Глобальный экземпляр RAG системы
rag_system = RAGSystem() 