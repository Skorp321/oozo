-- Функция для проверки существования таблиц
-- Используется для проверки перед применением миграций

CREATE OR REPLACE FUNCTION table_exists(table_name TEXT) 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = table_name
    );
END;
$$ LANGUAGE plpgsql;

-- Проверка существования схемы и таблиц
DO $$
BEGIN
    -- Проверка существования схемы
    IF NOT EXISTS (
        SELECT FROM information_schema.schemata 
        WHERE schema_name = 'oozo-schema'
    ) THEN
        RAISE NOTICE 'Схема oozo-schema не существует';
    ELSE
        RAISE NOTICE 'Схема oozo-schema существует';
    END IF;
    
    -- Проверка существования таблиц в схеме oozo-schema
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'chunks'
    ) THEN
        RAISE NOTICE 'Таблица oozo-schema.chunks не существует';
    ELSE
        RAISE NOTICE 'Таблица oozo-schema.chunks существует';
    END IF;
    
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'query_logs'
    ) THEN
        RAISE NOTICE 'Таблица oozo-schema.query_logs не существует';
    ELSE
        RAISE NOTICE 'Таблица oozo-schema.query_logs существует';
    END IF;
    
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'oozo-schema' 
        AND table_name = 'query_log_chunks'
    ) THEN
        RAISE NOTICE 'Таблица oozo-schema.query_log_chunks не существует';
    ELSE
        RAISE NOTICE 'Таблица oozo-schema.query_log_chunks существует';
    END IF;
END $$;

