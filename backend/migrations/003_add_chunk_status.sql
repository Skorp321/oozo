-- Миграция 003: Добавление поля status в таблицу chunks
-- Добавляет поле для хранения статуса чанка (actual/stored)

SET search_path TO "oozo-schema", public;

-- Добавляем поле status в таблицу chunks
ALTER TABLE "oozo-schema".chunks 
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'actual' NOT NULL;

-- Обновляем существующие записи - помечаем их как "stored" (так как они уже не новые)
UPDATE "oozo-schema".chunks 
SET status = 'stored' 
WHERE status = 'actual';

-- Создаем индекс для ускорения поиска по статусу
CREATE INDEX IF NOT EXISTS idx_chunks_status 
ON "oozo-schema".chunks(status);

COMMENT ON COLUMN "oozo-schema".chunks.status IS 'Статус чанка: actual (актуальный) или stored (хранимый)';
