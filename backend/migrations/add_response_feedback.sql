-- Миграция: add_response_feedback.sql
-- Таблица оценок (like/dislike), связана с query_logs.
-- Для существующей БД с старой версией таблицы — пересоздаём с новой структурой.

DROP TABLE IF EXISTS "oozo-schema".response_feedback;

CREATE TABLE "oozo-schema".response_feedback (
    id SERIAL PRIMARY KEY,
    query_log_id INTEGER NOT NULL,
    "like" BOOLEAN NOT NULL DEFAULT FALSE,
    dislike BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL,
    CONSTRAINT fk_response_feedback_query_log_id
        FOREIGN KEY (query_log_id)
        REFERENCES "oozo-schema".query_logs(id)
        ON DELETE CASCADE
);
COMMENT ON TABLE "oozo-schema".response_feedback IS 'Оценки пользователей (like/dislike) ответов бота из Streamlit';
COMMENT ON COLUMN "oozo-schema".response_feedback.id IS 'ID записи';
COMMENT ON COLUMN "oozo-schema".response_feedback.query_log_id IS 'ID ответа из таблицы query_logs';
COMMENT ON COLUMN "oozo-schema".response_feedback."like" IS 'Понравилось';
COMMENT ON COLUMN "oozo-schema".response_feedback.dislike IS 'Не понравилось';
COMMENT ON COLUMN "oozo-schema".response_feedback.created_at IS 'Дата создания в UTC';
CREATE INDEX idx_response_feedback_query_log_id ON "oozo-schema".response_feedback(query_log_id);
CREATE INDEX idx_response_feedback_created_at ON "oozo-schema".response_feedback(created_at);
