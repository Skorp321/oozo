# Миграции базы данных

Миграции базы данных выполняются через SQL скрипты, расположенные в директории `migrations/`.

## Структура

- `init_schema.sql` - единый скрипт для создания всей схемы базы данных с нуля

## Применение миграций

### Автоматическое применение

Миграции применяются автоматически при запуске приложения через функцию `init_db()` в `app/database.py`.

### Ручное применение

#### Вариант 1: Скрипт из корня проекта (рекомендуется)

```bash
# Локально (подключение к БД по настройкам из .env)
./apply_migrations.sh
# или явно
./apply_migrations.sh local

# Через Docker (контейнер rag-app подключается к postgres)
./apply_migrations.sh docker
```

#### Вариант 2: Через Python скрипт

```bash
cd backend
python scripts/apply_migrations.py
```

#### Вариант 3: Через Docker Compose

```bash
docker compose exec rag-app python scripts/apply_migrations.py
```

#### Вариант 4: Прямое применение SQL

```bash
# Подключение к PostgreSQL контейнеру
docker compose exec postgres psql -U rag_user -d rag_db

# Или применение через psql из файла
docker compose exec -T postgres psql -U rag_user -d rag_db < migrations/init_schema.sql
```

## Схема базы данных

Все таблицы создаются в схеме `oozo-schema`. Схема создается автоматически при применении миграции `init_schema.sql`.

## Структура таблиц

Все таблицы находятся в схеме `oozo-schema`:

### Таблица `oozo-schema.chunks`
Хранит чанки документов, используемые для создания векторной БД.

**Поля:**
- `id` - ID чанка (SERIAL PRIMARY KEY)
- `content` - Текст чанка (TEXT NOT NULL)
- `document_title` - Название документа (VARCHAR(500))
- `file_path` - Путь к файлу (VARCHAR(1000))
- `file_hash` - SHA256 хэш-сумма файла (VARCHAR(64))
- `chunk_index` - Индекс чанка в документе (INTEGER)
- `total_chunks` - Всего чанков в документе (INTEGER)
- `status` - Статус чанка: actual (актуальный) или stored (хранимый) (VARCHAR(50), DEFAULT 'actual')
- `metadata_json` - Дополнительные метаданные в JSON формате (TEXT)
- `created_at` - Дата создания (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

**Индексы:**
- `idx_chunks_document_title` - по document_title
- `idx_chunks_file_path` - по file_path
- `idx_chunks_file_hash` - по file_hash
- `idx_chunks_status` - по status

### Таблица `oozo-schema.query_logs`
Хранит логи запросов пользователей к системе.

**Поля:**
- `id` - ID записи (SERIAL PRIMARY KEY)
- `user_login` - Логин пользователя (VARCHAR(255))
- `user_ip` - IP адрес пользователя (VARCHAR(45))
- `question` - Вопрос пользователя (TEXT NOT NULL)
- `final_prompt` - Финальный промпт, отправленный в LLM (TEXT)
- `answer` - Ответ системы (TEXT)
- `processing_time` - Время обработки в секундах (VARCHAR(50))
- `error_message` - Сообщение об ошибке, если есть (TEXT)
- `status` - Статус: success или error (VARCHAR(50), DEFAULT 'success')
- `created_at` - Дата создания записи (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

**Индексы:**
- `idx_query_logs_user_login` - по user_login
- `idx_query_logs_user_ip` - по user_ip
- `idx_query_logs_status` - по status
- `idx_query_logs_created_at` - по created_at

### Таблица `oozo-schema.query_log_chunks`
Промежуточная таблица для связи many-to-many между `query_logs` и `chunks`.

**Поля:**
- `query_log_id` - ID записи из query_logs (INTEGER NOT NULL, FOREIGN KEY)
- `chunk_id` - ID чанка из chunks (INTEGER NOT NULL, FOREIGN KEY)
- PRIMARY KEY (query_log_id, chunk_id)

**Внешние ключи:**
- `fk_query_log_chunks_query_log_id` → `oozo-schema.query_logs(id)` ON DELETE CASCADE
- `fk_query_log_chunks_chunk_id` → `oozo-schema.chunks(id)` ON DELETE CASCADE

**Индексы:**
- `idx_query_log_chunks_query_log_id` - по query_log_id
- `idx_query_log_chunks_chunk_id` - по chunk_id

## Проверка состояния миграций

Для проверки какие таблицы существуют в БД:

```bash
# Показать все таблицы в схеме oozo-schema
docker compose exec postgres psql -U rag_user -d rag_db -c "\dt oozo-schema.*"

# Показать все схемы
docker compose exec postgres psql -U rag_user -d rag_db -c "\dn"
```
