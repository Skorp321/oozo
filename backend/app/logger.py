import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from .schemas import QueryRequest, QueryResponse
from .config import settings
from .database import get_db_session
from .models import QueryLog, Chunk, query_log_chunks


class QALogger:
    """
    Логгер для записи вопросов и ответов в файл
    """
    
    def __init__(self, log_file: str = None):
        if log_file is None:
            log_file = settings.logs_path
        self.log_file = Path(log_file)
        self.logger = logging.getLogger(__name__)
        
        # Создаем директорию для логов если её нет
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Настраиваем форматтер для JSON логов
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def log_qa(self, request: QueryRequest, response: QueryResponse, 
                processing_time: Optional[float] = None, 
                error: Optional[str] = None,
                user_login: Optional[str] = None,
                user_ip: Optional[str] = None,
                final_prompt: Optional[str] = None,
                chunk_ids: Optional[List[int]] = None,
                user_timezone: Optional[str] = None) -> None:
        """
        Логирует вопрос и ответ в БД
        
        Args:
            request: Запрос пользователя
            response: Ответ системы
            processing_time: Время обработки в секундах
            error: Сообщение об ошибке, если есть
            user_login: Логин пользователя
            user_ip: IP адрес пользователя
            final_prompt: Финальный промпт, отправленный в LLM
            chunk_ids: Список ID чанков, использованных для ответа
            user_timezone: Временная зона пользователя (например, Europe/Moscow, UTC)
        """
        try:
            # Проверяем, что ответ не пустой (если нет ошибки)
            if not response.answer and not error:
                self.logger.warning(f"Пустой ответ для вопроса: '{request.question[:50]}...'")
            
            
            # Записываем в БД
            try:
                with get_db_session() as db:
                    db_log = QueryLog(
                        user_login=user_login,
                        user_ip=user_ip,
                        question=request.question,
                        final_prompt=final_prompt,
                        answer=response.answer,
                        processing_time=str(processing_time) if processing_time else None,
                        error_message=error,
                        status="error" if error else "success",
                        timezone=user_timezone,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(db_log)
                    db.flush()  # Получаем ID без коммита
                    
                    # Связываем чанки если есть
                    if chunk_ids:
                        self.logger.info(f"Попытка связать чанки: chunk_ids={chunk_ids}")
                        # Вставляем связи между логом и чанками в таблицу query_log_chunks
                        from sqlalchemy import insert
                        db.execute(
                            insert(query_log_chunks),
                            [
                                {"query_log_id": db_log.id, "chunk_id": chunk_id}
                                for chunk_id in chunk_ids
                                if chunk_id is not None
                            ]
                        )
                        # Проверяем, что чанки существуют в БД
                        chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
                        self.logger.info(f"Найдено чанков в БД: {len(chunks)} из {len(chunk_ids)} запрошенных")
                        if len(chunks) != len(chunk_ids):
                            missing_ids = set(chunk_ids) - {c.id for c in chunks}
                            self.logger.warning(f"Некоторые чанки не найдены в БД: {missing_ids}")
                    else:
                        self.logger.warning(f"chunk_ids пустой или None при логировании")
                    
                    db.commit()
                    self.logger.info(f"QA лог записан в БД с ID: {db_log.id}, связано чанков: {len(db_log.chunks)}")
            except Exception as db_error:
                self.logger.error(f"Ошибка при записи QA лога в БД: {db_error}")
            
            self.logger.info(f"QA лог записан: вопрос='{request.question[:50]}...', ответ={len(response.answer)} символов")
            
        except Exception as e:
            self.logger.error(f"Ошибка при записи QA лога: {e}")
    
    def log_stream_qa(self, question: str, answer: str, 
                     sources_count: int = 0,
                     sources_payload: Optional[list] = None,
                     processing_time: Optional[float] = None,
                     error: Optional[str] = None,
                     user_login: Optional[str] = None,
                     user_ip: Optional[str] = None,
                     final_prompt: Optional[str] = None,
                     chunk_ids: Optional[List[int]] = None,
                     user_timezone: Optional[str] = None) -> None:
        """
        Логирует потоковый вопрос и ответ
        
        Args:
            question: Вопрос пользователя
            answer: Ответ системы
            sources_count: Количество источников
            sources_payload: Данные источников
            processing_time: Время обработки в секундах
            error: Сообщение об ошибке, если есть
            user_login: Логин пользователя
            user_ip: IP адрес пользователя
            final_prompt: Финальный промпт, отправленный в LLM
            chunk_ids: Список ID чанков, использованных для ответа
            user_timezone: Временная зона пользователя (например, Europe/Moscow, UTC)
        """
        try:
            # Проверяем, что ответ не пустой (если нет ошибки)
            if not answer and not error:
                self.logger.warning(f"Пустой ответ для вопроса: '{question[:50]}...'")

            # Записываем в БД
            try:
                with get_db_session() as db:
                    db_log = QueryLog(
                        user_login=user_login,
                        user_ip=user_ip,
                        question=question,
                        final_prompt=final_prompt,
                        answer=answer,
                        processing_time=str(processing_time) if processing_time else None,
                        error_message=error,
                        status="error" if error else "success",
                        timezone=user_timezone,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(db_log)
                    db.flush()  # Получаем ID без коммита
                    
                    # Связываем чанки если есть
                    if chunk_ids:
                        self.logger.info(f"Попытка связать чанки: chunk_ids={chunk_ids}")
                        # Вставляем связи между логом и чанками в таблицу query_log_chunks
                        from sqlalchemy import insert
                        db.execute(
                            insert(query_log_chunks),
                            [
                                {"query_log_id": db_log.id, "chunk_id": chunk_id}
                                for chunk_id in chunk_ids
                                if chunk_id is not None
                            ]
                        )
                        # Проверяем, что чанки существуют в БД
                        chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
                        self.logger.info(f"Найдено чанков в БД: {len(chunks)} из {len(chunk_ids)} запрошенных")
                        if len(chunks) != len(chunk_ids):
                            missing_ids = set(chunk_ids) - {c.id for c in chunks}
                            self.logger.warning(f"Некоторые чанки не найдены в БД: {missing_ids}")
                    else:
                        self.logger.warning(f"chunk_ids пустой или None при логировании")
                    
                    db.commit()
                    self.logger.info(f"Stream QA лог записан в БД с ID: {db_log.id}, связано чанков: {len(db_log.chunks)}")
            except Exception as db_error:
                self.logger.error(f"Ошибка при записи stream QA лога в БД: {db_error}")
            
            self.logger.info(f"Stream QA лог записан: вопрос='{question[:50]}...', ответ={len(answer)} символов")
            
        except Exception as e:
            self.logger.error(f"Ошибка при записи stream QA лога: {e}")
    
    def get_logs(self, limit: int = 100) -> list:
        """
        Получает последние логи
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список последних логов
        """
        try:
            if not self.log_file.exists():
                return []
            
            logs = []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
            
            return logs[-limit:] if limit else logs
            
        except Exception as e:
            self.logger.error(f"Ошибка при чтении логов: {e}")
            return []


# Глобальный экземпляр логгера
qa_logger = QALogger()
