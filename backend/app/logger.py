import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from sqlalchemy import Table, MetaData, insert
from .schemas import QueryRequest, QueryResponse
from .config import settings
from .database import get_db_session, engine
from .models import QueryLog, Chunk, query_log_chunks, SCHEMA_NAME


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
                user_timezone: Optional[str] = None) -> Optional[int]:
        """
        Логирует вопрос и ответ в БД. Возвращает ID созданной записи query_logs или None.
        
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
                    linked_chunks_count = 0
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
                    
                    # Связываем чанки если есть (без риска завалить логирование ответа)
                    if chunk_ids:
                        clean_chunk_ids = self._get_valid_chunk_ids(db, chunk_ids)
                        if clean_chunk_ids:
                            self.logger.info(f"Пробуем связать чанки: {clean_chunk_ids}")
                            try:
                                db.execute(
                                    insert(query_log_chunks),
                                    [
                                        {"query_log_id": db_log.id, "chunk_id": chunk_id}
                                        for chunk_id in clean_chunk_ids
                                    ]
                                )
                                linked_chunks_count = len(clean_chunk_ids)
                            except Exception as chunk_link_error:
                                # Не прерываем сохранение ответа, даже если связи с чанками не удалось записать
                                self.logger.warning(
                                    "Не удалось связать chunk_ids с query_log_id=%s: %s",
                                    db_log.id,
                                    chunk_link_error,
                                )
                        else:
                            self.logger.warning("После очистки не осталось валидных chunk_ids для связи")
                    else:
                        self.logger.warning("chunk_ids пустой или None при логировании")
                    
                    self.logger.info(
                        "QA лог записан в БД с ID: %s, связано чанков: %s",
                        db_log.id,
                        linked_chunks_count,
                    )
                    return db_log.id
            except Exception as db_error:
                self.logger.error("Ошибка при записи QA лога в БД: %s", db_error, exc_info=True)
                fallback_id = self._insert_query_log_fallback(
                    question=request.question,
                    answer=response.answer,
                    processing_time=processing_time,
                    error=error,
                    user_login=user_login,
                    user_ip=user_ip,
                    final_prompt=final_prompt,
                    user_timezone=user_timezone,
                )
                if fallback_id is not None:
                    self.logger.warning("QA лог записан через fallback insert. id=%s", fallback_id)
                    return fallback_id
            
            self.logger.info(f"QA лог записан: вопрос='{request.question[:50]}...', ответ={len(response.answer)} символов")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка при записи QA лога: {e}")
            return None
    
    def log_stream_qa(self, question: str, answer: str, 
                     sources_count: int = 0,
                     sources_payload: Optional[list] = None,
                     processing_time: Optional[float] = None,
                     error: Optional[str] = None,
                     user_login: Optional[str] = None,
                     user_ip: Optional[str] = None,
                     final_prompt: Optional[str] = None,
                     chunk_ids: Optional[List[int]] = None,
                     user_timezone: Optional[str] = None) -> Optional[int]:
        """
        Логирует потоковый вопрос и ответ. Возвращает ID созданной записи query_logs или None.
        
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
                    linked_chunks_count = 0
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
                    
                    # Связываем чанки если есть (без риска завалить логирование ответа)
                    if chunk_ids:
                        clean_chunk_ids = self._get_valid_chunk_ids(db, chunk_ids)
                        if clean_chunk_ids:
                            self.logger.info(f"Пробуем связать чанки: {clean_chunk_ids}")
                            try:
                                db.execute(
                                    insert(query_log_chunks),
                                    [
                                        {"query_log_id": db_log.id, "chunk_id": chunk_id}
                                        for chunk_id in clean_chunk_ids
                                    ]
                                )
                                linked_chunks_count = len(clean_chunk_ids)
                            except Exception as chunk_link_error:
                                # Не прерываем сохранение ответа, даже если связи с чанками не удалось записать
                                self.logger.warning(
                                    "Не удалось связать chunk_ids с query_log_id=%s: %s",
                                    db_log.id,
                                    chunk_link_error,
                                )
                        else:
                            self.logger.warning("После очистки не осталось валидных chunk_ids для связи")
                    else:
                        self.logger.warning("chunk_ids пустой или None при логировании")
                    
                    self.logger.info(
                        "Stream QA лог записан в БД с ID: %s, связано чанков: %s",
                        db_log.id,
                        linked_chunks_count,
                    )
                    return db_log.id
            except Exception as db_error:
                self.logger.error("Ошибка при записи stream QA лога в БД: %s", db_error, exc_info=True)
                fallback_id = self._insert_query_log_fallback(
                    question=question,
                    answer=answer,
                    processing_time=processing_time,
                    error=error,
                    user_login=user_login,
                    user_ip=user_ip,
                    final_prompt=final_prompt,
                    user_timezone=user_timezone,
                )
                if fallback_id is not None:
                    self.logger.warning("Stream QA лог записан через fallback insert. id=%s", fallback_id)
                    return fallback_id
            
            self.logger.info(f"Stream QA лог записан: вопрос='{question[:50]}...', ответ={len(answer)} символов")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка при записи stream QA лога: {e}")
            return None

    def _get_valid_chunk_ids(self, db, chunk_ids: Optional[List[int]]) -> List[int]:
        """Нормализует chunk_ids: убирает None/дубли/нечисловые и оставляет только существующие в БД."""
        if not chunk_ids:
            return []

        normalized: List[int] = []
        seen = set()
        for chunk_id in chunk_ids:
            if chunk_id is None:
                continue
            try:
                cid = int(chunk_id)
            except (TypeError, ValueError):
                continue
            if cid in seen:
                continue
            seen.add(cid)
            normalized.append(cid)

        if not normalized:
            return []

        existing_chunks = db.query(Chunk.id).filter(Chunk.id.in_(normalized)).all()
        existing_ids = {row[0] for row in existing_chunks}
        valid_ids = [cid for cid in normalized if cid in existing_ids]

        if len(valid_ids) != len(normalized):
            missing_ids = sorted(set(normalized) - set(valid_ids))
            self.logger.warning(f"Исключены отсутствующие chunk_ids: {missing_ids}")

        return valid_ids

    def _insert_query_log_fallback(
        self,
        question: str,
        answer: str,
        processing_time: Optional[float],
        error: Optional[str],
        user_login: Optional[str],
        user_ip: Optional[str],
        final_prompt: Optional[str],
        user_timezone: Optional[str],
    ) -> Optional[int]:
        """
        Резервная вставка в query_logs без связей с чанками.
        Использует только реально существующие в таблице колонки.
        """
        try:
            metadata = MetaData()
            query_logs_table = Table(
                "query_logs",
                metadata,
                schema=SCHEMA_NAME,
                autoload_with=engine,
            )

            values = {
                "user_login": user_login,
                "user_ip": user_ip,
                "question": question,
                "final_prompt": final_prompt,
                "answer": answer,
                "processing_time": str(processing_time) if processing_time else None,
                "error_message": error,
                "status": "error" if error else "success",
                "timezone": user_timezone,
                "created_at": datetime.now(timezone.utc),
            }

            filtered_values = {k: v for k, v in values.items() if k in query_logs_table.c}
            if "question" not in filtered_values:
                self.logger.error("Fallback insert невозможен: в query_logs отсутствует колонка question")
                return None

            stmt = insert(query_logs_table).values(**filtered_values).returning(query_logs_table.c.id)
            with engine.begin() as conn:
                new_id = conn.execute(stmt).scalar_one()
            return int(new_id)
        except Exception as e:
            self.logger.error("Fallback insert в query_logs завершился ошибкой: %s", e, exc_info=True)
            return None
    
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
