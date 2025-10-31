from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

# Имя схемы для всех таблиц
SCHEMA_NAME = "oozo-schema"

# Промежуточная таблица для связи many-to-many между query_logs и chunks
query_log_chunks = Table(
    'query_log_chunks',
    Base.metadata,
    Column('query_log_id', Integer, ForeignKey(f'{SCHEMA_NAME}.query_logs.id', ondelete='CASCADE'), primary_key=True),
    Column('chunk_id', Integer, ForeignKey(f'{SCHEMA_NAME}.chunks.id', ondelete='CASCADE'), primary_key=True),
    schema=SCHEMA_NAME
)


class Chunk(Base):
    """
    Таблица для хранения чанков, из которых создается векторная БД
    """
    __tablename__ = "chunks"
    __table_args__ = {'schema': SCHEMA_NAME}
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False, comment="Текст чанка")
    document_title = Column(String(500), nullable=True, comment="Название документа")
    file_path = Column(String(1000), nullable=True, comment="Путь к файлу")
    file_hash = Column(String(64), nullable=True, comment="SHA256 хэш-сумма файла")
    chunk_index = Column(Integer, nullable=True, comment="Индекс чанка в документе")
    total_chunks = Column(Integer, nullable=True, comment="Всего чанков в документе")
    status = Column(String(10), default="actual", nullable=False, comment="Статус чанка: actual (актуальный) или stored (хранимый)")
    metadata_json = Column(Text, nullable=True, comment="Дополнительные метаданные в JSON формате")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Дата создания")
    
    # Связь с query_logs через промежуточную таблицу
    query_logs = relationship("QueryLog", secondary=query_log_chunks, back_populates="chunks")


class QueryLog(Base):
    """
    Таблица для логирования запросов пользователей
    """
    __tablename__ = "query_logs"
    __table_args__ = {'schema': SCHEMA_NAME}
    
    id = Column(Integer, primary_key=True, index=True)
    user_login = Column(String(255), nullable=True, comment="Логин пользователя")
    user_ip = Column(String(45), nullable=True, comment="IP адрес пользователя")
    question = Column(Text, nullable=False, comment="Вопрос пользователя")
    final_prompt = Column(Text, nullable=True, comment="Финальный промпт, отправленный в LLM")
    answer = Column(Text, nullable=True, comment="Ответ системы")
    processing_time = Column(String(50), nullable=True, comment="Время обработки в секундах")
    error_message = Column(Text, nullable=True, comment="Сообщение об ошибке, если есть")
    status = Column(String(50), default="success", nullable=False, comment="Статус: success или error")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Дата создания записи")
    
    # Связь с chunks через промежуточную таблицу
    chunks = relationship("Chunk", secondary=query_log_chunks, back_populates="query_logs")

