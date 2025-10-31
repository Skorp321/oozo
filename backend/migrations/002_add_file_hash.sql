-- Миграция 002: Добавление поля file_hash в таблицу chunks
-- Добавляет поле для хранения SHA256 хэш-суммы файла

SET search_path TO "oozo-schema", public;

-- Добавляем поле file_hash в таблицу chunks
ALTER TABLE "oozo-schema".chunks 
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64) NULL 
COMMENT 'SHA256 хэш-сумма файла';

-- Создаем индекс для ускорения поиска по хэшу
CREATE INDEX IF NOT EXISTS idx_chunks_file_hash 
ON "oozo-schema".chunks(file_hash);

COMMENT ON COLUMN "oozo-schema".chunks.file_hash IS 'SHA256 хэш-сумма файла';
