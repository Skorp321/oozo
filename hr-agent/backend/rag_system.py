import os
import logging
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from datetime import datetime

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from .config import settings
from dotenv import load_dotenv
from .document_processor import load_docx_files, split_documents, get_document_stats

load_dotenv()
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
        self.retriever = None
        self._initialized = False
        self._embedding_error = None
    
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
            api_base = (
                settings.embedding_api_base
                or settings.openai_api_base
                or "http://localhost:8000/v1"
            )
            api_key = settings.embedding_api_key or settings.openai_api_key or "dummy_key"

            logger.info(
                "Инициализация эмбеддинговой модели %s (api_base=%s)",
                settings.embedding_model_name,
                api_base,
            )

            candidate_embeddings = OpenAIEmbeddings(
                model=settings.embedding_model_name,
                openai_api_key=api_key,
                openai_api_base=api_base,
                timeout=600,
            )

            # Проверяем доступность эндпоинта заранее, чтобы не падать во время старта MCP.
            candidate_embeddings.embed_query("healthcheck")
            self.embeddings = candidate_embeddings
            self._embedding_error = None
            logger.info("Модель эмбеддингов создана и проверена")
        except Exception as e:
            self.embeddings = None
            self._embedding_error = str(e)
            logger.warning(
                "Эмбеддинги недоступны, RAG продолжит работу в BM25-only режиме: %s",
                e,
            )

    def _init_bm25_only_retriever(self):
        """Создание BM25 ретривера без векторного поиска."""
        self.documents = load_docx_files(settings.docs_path)
        chunks = split_documents(self.documents) if self.documents else []

        if chunks:
            self.retriever = BM25Retriever.from_documents(chunks)
            self.vector_store = None
            self._update_stats(chunks)
            logger.info("Создан BM25-only ретривер: %s чанков", len(chunks))
        else:
            self.retriever = None
            self.vector_store = None
            self.stats = {
                "total_documents": 0,
                "total_chunks": 0,
                "index_size_mb": 0,
                "last_updated": datetime.now().isoformat()
            }
            logger.warning("Документы для BM25 не найдены")
    
    def _load_or_create_vector_store(self):
        """
        Загрузка существующего или создание нового векторного хранилища
        """
        if self.embeddings is None:
            logger.warning(
                "Пропускаем инициализацию FAISS: эмбеддинги недоступны (%s)",
                self._embedding_error or "unknown error",
            )
            self._init_bm25_only_retriever()
            return

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
            
            if not self.embeddings:
                logger.warning("Эмбеддинги недоступны, используем только BM25")
                self.vector_store = None
                self.retriever = BM25Retriever.from_documents(chunks)
                self._update_stats(chunks)
                return

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
        repo_id = settings.openai_model_name or "model-run-vekow-trunk"
        api_base = settings.openai_api_base or "https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1"

        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            openai_api_base=api_base,
            model=repo_id,
            temperature=settings.temperature,
            streaming=False,  # Для MCP не нужен streaming
            timeout=600
        )

    def retrieve_documents(self, question: str, k: int = 5):
        """
        Получение релевантных документов с использованием текущего эмбеддера
        """
        if not self._initialized or not self.vector_store:
            return []
        
        try:
            if self.retriever is not None:
                return self.retriever.invoke(question)
            return self.vector_store.similarity_search(question, k=k)
        except Exception as exc:
            logger.error(f"Ошибка при получении документов: {exc}")
            return []
    
    def query(self, question: str, return_sources: bool = True) -> Dict[str, Any]:
        """
        Выполнение запроса к RAG системе
        """
        
        # Создание промпта
        template = """Ты - помощник по HR вопросам. Используй следующие части контекста из документов, чтобы дать точный и полезный ответ на вопрос пользователя.

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
                try:
                    chunks = self.retriever.invoke(question)
                except Exception as retriever_error:
                    logger.error("Ошибка retriever.invoke, fallback на BM25: %s", retriever_error)
                    if self.documents:
                        fallback_chunks = split_documents(self.documents)
                        if fallback_chunks:
                            bm25 = BM25Retriever.from_documents(fallback_chunks)
                            chunks = bm25.invoke(question)
                        else:
                            chunks = []
                    else:
                        chunks = []
            context = format_documents(chunks)
            
            # Формируем финальный промпт из шаблона
            final_prompt = template.format(context=context, question=question)
            
            chain = prompt | self.llm
            result = chain.invoke({"context": context, "question": question})
            
            result = format_answer(result)

            # Обработка результата
            answer = result if result else "Не удалось получить ответ"

            # Используем те же чанки для источников
            source_documents = chunks if isinstance(chunks, list) else self.vector_store.similarity_search(question, k=5)
            logger.info(f"Тип чанков {type(source_documents)}")
            logger.info(f"Найденные чанки: {len(source_documents) if isinstance(source_documents, list) else 'N/A'}")
            
            # Формирование источников
            sources = []
            if return_sources and source_documents:
                if isinstance(source_documents, list):
                    for doc in source_documents:
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            sources.append({
                                "title": doc.metadata.get("title", "Неизвестный источник"),
                                "content": doc.page_content,
                                "score": 1.0,
                                "metadata": doc.metadata
                            })
            
            logger.info(f"Запрос обработан, найдено источников: {len(sources)}")
            
            return {
                "answer": answer,
                "sources": sources,
                "final_prompt": final_prompt
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            
            return {
                "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
                "sources": [],
                "final_prompt": None
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики системы
        """
        return self.stats.copy()


# Глобальный экземпляр RAG системы
rag_system = RAGSystem()
