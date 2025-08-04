import os
import logging
from typing import List, Dict, Any
from pathlib import Path
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangChainDocument
from .config import settings

logger = logging.getLogger(__name__)


def load_docx_files(docs_path: str) -> List[Dict[str, Any]]:
    """
    Загружает все .docx файлы из указанной папки
    """
    documents = []
    docs_dir = Path(docs_path)
    
    if not docs_dir.exists():
        logger.warning(f"Папка документов не найдена: {docs_path}")
        return documents
    
    for file_path in docs_dir.glob("*.docx"):
        try:
            logger.info(f"Загрузка документа: {file_path}")
            text = extract_text_from_docx(str(file_path))
            if text.strip():
                documents.append({
                    "title": file_path.stem,
                    "content": text,
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size
                })
                logger.info(f"Документ загружен: {file_path.name} ({len(text)} символов)")
            else:
                logger.warning(f"Документ пустой: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке документа {file_path}: {e}")
    
    logger.info(f"Загружено документов: {len(documents)}")
    return documents


def extract_text_from_docx(file_path: str) -> str:
    """
    Извлекает текст из .docx файла
    """
    try:
        doc = Document(file_path)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
        
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из {file_path}: {e}")
        raise


def split_documents(documents: List[Dict[str, Any]], 
                   chunk_size: int = None, 
                   chunk_overlap: int = None) -> List[LangChainDocument]:
    """
    Разбивает документы на чанки с помощью RecursiveCharacterTextSplitter
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = settings.chunk_overlap
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    langchain_docs = []
    
    for doc in documents:
        try:
            # Создаем LangChain Document
            langchain_doc = LangChainDocument(
                page_content=doc["content"],
                metadata={
                    "title": doc["title"],
                    "file_path": doc["file_path"],
                    "file_size": doc["file_size"],
                    "source": doc["title"]
                }
            )
            
            # Разбиваем на чанки
            chunks = text_splitter.split_documents([langchain_doc])
            
            # Добавляем информацию о чанке в метаданные
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                })
            
            langchain_docs.extend(chunks)
            logger.info(f"Документ '{doc['title']}' разбит на {len(chunks)} чанков")
            
        except Exception as e:
            logger.error(f"Ошибка при разбивке документа '{doc['title']}': {e}")
    
    logger.info(f"Всего создано чанков: {len(langchain_docs)}")
    return langchain_docs


def get_document_stats(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Возвращает статистику по документам
    """
    if not documents:
        return {
            "total_documents": 0,
            "total_characters": 0,
            "total_size_bytes": 0,
            "average_document_size": 0
        }
    
    total_chars = sum(len(doc["content"]) for doc in documents)
    total_size = sum(doc["file_size"] for doc in documents)
    
    return {
        "total_documents": len(documents),
        "total_characters": total_chars,
        "total_size_bytes": total_size,
        "average_document_size": total_size / len(documents)
    } 