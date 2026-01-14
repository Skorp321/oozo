-- Миграция: add_timezone_field.sql
-- Добавление поля timezone в таблицу query_logs и изменение created_at на UTC
-- Эта миграция обновляет существующую таблицу

-- Установка схемы по умолчанию для текущей сессии
SET search_path TO "oozo-schema", public;

-- Добавляем поле timezone если его еще нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'query_logs' 
        AND column_name = 'timezone'
    ) THEN
        ALTER TABLE "oozo-schema".query_logs 
        ADD COLUMN timezone VARCHAR(50);
        
        COMMENT ON COLUMN "oozo-schema".query_logs.timezone IS 'Временная зона пользователя (например, Europe/Moscow, UTC)';
    END IF;
END $$;

-- Изменяем тип created_at на TIMESTAMP WITH TIME ZONE если еще не изменен
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'query_logs' 
        AND column_name = 'created_at'
        AND data_type = 'timestamp without time zone'
    ) THEN
        -- Конвертируем существующие значения в UTC
        ALTER TABLE "oozo-schema".query_logs 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC';
        
        -- Устанавливаем значение по умолчанию для новых записей
        ALTER TABLE "oozo-schema".query_logs 
        ALTER COLUMN created_at SET DEFAULT (NOW() AT TIME ZONE 'UTC');
        
        COMMENT ON COLUMN "oozo-schema".query_logs.created_at IS 'Дата создания записи в UTC';
    END IF;
END $$;

-- Также обновляем таблицу chunks для единообразия
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'chunks' 
        AND column_name = 'created_at'
        AND data_type = 'timestamp without time zone'
    ) THEN
        -- Конвертируем существующие значения в UTC
        ALTER TABLE "oozo-schema".chunks 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC';
        
        -- Устанавливаем значение по умолчанию для новых записей
        ALTER TABLE "oozo-schema".chunks 
        ALTER COLUMN created_at SET DEFAULT (NOW() AT TIME ZONE 'UTC');
        
        COMMENT ON COLUMN "oozo-schema".chunks.created_at IS 'Дата создания в UTC';
    END IF;
END $$;
