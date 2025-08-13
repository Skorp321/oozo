import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .schemas import QueryRequest, QueryResponse
from .config import settings


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
                error: Optional[str] = None) -> None:
        """
        Логирует вопрос и ответ в JSONL формате
        
        Args:
            request: Запрос пользователя
            response: Ответ системы
            processing_time: Время обработки в секундах
            error: Сообщение об ошибке, если есть
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request": {
                    "question": request.question,
                    "return_sources": request.return_sources
                },
                "response": {
                    "answer": response.answer,
                    "sources_count": len(response.sources) if response.sources else 0
                },
                "processing_time_seconds": processing_time,
                "error": error,
                "status": "error" if error else "success"
            }
            
            # Записываем в JSONL файл
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            self.logger.info(f"QA лог записан: вопрос='{request.question[:50]}...'")
            
        except Exception as e:
            self.logger.error(f"Ошибка при записи QA лога: {e}")
    
    def log_stream_qa(self, question: str, answer: str, 
                     sources_count: int = 0,
                     processing_time: Optional[float] = None,
                     error: Optional[str] = None) -> None:
        """
        Логирует потоковый вопрос и ответ
        
        Args:
            question: Вопрос пользователя
            answer: Ответ системы
            sources_count: Количество источников
            processing_time: Время обработки в секундах
            error: Сообщение об ошибке, если есть
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "stream",
                "request": {
                    "question": question,
                    "return_sources": True
                },
                "response": {
                    "answer": answer,
                    "sources_count": sources_count
                },
                "processing_time_seconds": processing_time,
                "error": error,
                "status": "error" if error else "success"
            }
            
            # Записываем в JSONL файл
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            self.logger.info(f"Stream QA лог записан: вопрос='{question[:50]}...'")
            
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
    
    def clear_logs(self) -> None:
        """
        Очищает файл логов
        """
        try:
            if self.log_file.exists():
                self.log_file.unlink()
            self.logger.info("Логи очищены")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке логов: {e}")


# Глобальный экземпляр логгера
qa_logger = QALogger()
