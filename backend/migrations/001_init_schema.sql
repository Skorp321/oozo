-- Миграция: 001_init_schema.sql
-- Создание схемы oozo-schema и таблиц для логирования работы RAG агента
-- Дата создания: 2024

-- Создание схемы oozo-schema если её нет
CREATE SCHEMA IF NOT EXISTS "oozo-schema";

-- Установка схемы по умолчанию для текущей сессии (опционально, для удобства)
SET search_path TO "oozo-schema", public;

-- Таблица для хранения чанков из векторной БД
CREATE TABLE IF NOT EXISTS "oozo-schema".chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    document_title VARCHAR(500),
    file_path VARCHAR(1000),
    chunk_index INTEGER,
    total_chunks INTEGER,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Комментарии к таблице chunks
COMMENT ON TABLE "oozo-schema".chunks IS 'Таблица для хранения чанков, из которых создается векторная БД';
COMMENT ON COLUMN "oozo-schema".chunks.id IS 'ID чанка';
COMMENT ON COLUMN "oozo-schema".chunks.content IS 'Текст чанка';
COMMENT ON COLUMN "oozo-schema".chunks.document_title IS 'Название документа';
COMMENT ON COLUMN "oozo-schema".chunks.file_path IS 'Путь к файлу';
COMMENT ON COLUMN "oozo-schema".chunks.chunk_index IS 'Индекс чанка в документе';
COMMENT ON COLUMN "oozo-schema".chunks.total_chunks IS 'Всего чанков в документе';
COMMENT ON COLUMN "oozo-schema".chunks.metadata_json IS 'Дополнительные метаданные в JSON формате';
COMMENT ON COLUMN "oozo-schema".chunks.created_at IS 'Дата создания';

-- Создание индекса для быстрого поиска по document_title
CREATE INDEX IF NOT EXISTS idx_chunks_document_title ON "oozo-schema".chunks(document_title);

-- Создание индекса для быстрого поиска по file_path
CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON "oozo-schema".chunks(file_path);

-- Таблица для логирования запросов пользователей
CREATE TABLE IF NOT EXISTS "oozo-schema".query_logs (
    id SERIAL PRIMARY KEY,
    user_login VARCHAR(255),
    user_ip VARCHAR(45),
    question TEXT NOT NULL,
    final_prompt TEXT,
    answer TEXT,
    processing_time VARCHAR(50),
    error_message TEXT,
    status VARCHAR(50) DEFAULT 'success' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Комментарии к таблице query_logs
COMMENT ON TABLE "oozo-schema".query_logs IS 'Таблица для логирования запросов пользователей';
COMMENT ON COLUMN "oozo-schema".query_logs.id IS 'ID записи';
COMMENT ON COLUMN "oozo-schema".query_logs.user_login IS 'Логин пользователя';
COMMENT ON COLUMN "oozo-schema".query_logs.user_ip IS 'IP адрес пользователя';
COMMENT ON COLUMN "oozo-schema".query_logs.question IS 'Вопрос пользователя';
COMMENT ON COLUMN "oozo-schema".query_logs.final_prompt IS 'Финальный промпт, отправленный в LLM';
COMMENT ON COLUMN "oozo-schema".query_logs.answer IS 'Ответ системы';
COMMENT ON COLUMN "oozo-schema".query_logs.processing_time IS 'Время обработки в секундах';
COMMENT ON COLUMN "oozo-schema".query_logs.error_message IS 'Сообщение об ошибке, если есть';
COMMENT ON COLUMN "oozo-schema".query_logs.status IS 'Статус: success или error';
COMMENT ON COLUMN "oozo-schema".query_logs.created_at IS 'Дата создания записи';

-- Создание индексов для query_logs
CREATE INDEX IF NOT EXISTS idx_query_logs_user_login ON "oozo-schema".query_logs(user_login);
CREATE INDEX IF NOT EXISTS idx_query_logs_user_ip ON "oozo-schema".query_logs(user_ip);
CREATE INDEX IF NOT EXISTS idx_query_logs_status ON "oozo-schema".query_logs(status);
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON "oozo-schema".query_logs(created_at);

-- Промежуточная таблица для связи many-to-many между query_logs и chunks
CREATE TABLE IF NOT EXISTS "oozo-schema".query_log_chunks (
    query_log_id INTEGER NOT NULL,
    chunk_id INTEGER NOT NULL,
    PRIMARY KEY (query_log_id, chunk_id),
    CONSTRAINT fk_query_log_chunks_query_log_id 
        FOREIGN KEY (query_log_id) 
        REFERENCES "oozo-schema".query_logs(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_query_log_chunks_chunk_id 
        FOREIGN KEY (chunk_id) 
        REFERENCES "oozo-schema".chunks(id) 
        ON DELETE CASCADE
);

-- Комментарии к промежуточной таблице
COMMENT ON TABLE "oozo-schema".query_log_chunks IS 'Промежуточная таблица для связи many-to-many между query_logs и chunks';
COMMENT ON COLUMN "oozo-schema".query_log_chunks.query_log_id IS 'ID записи из query_logs';
COMMENT ON COLUMN "oozo-schema".query_log_chunks.chunk_id IS 'ID чанка из chunks';

-- Создание индексов для промежуточной таблицы
CREATE INDEX IF NOT EXISTS idx_query_log_chunks_query_log_id ON "oozo-schema".query_log_chunks(query_log_id);
CREATE INDEX IF NOT EXISTS idx_query_log_chunks_chunk_id ON "oozo-schema".query_log_chunks(chunk_id);


