# Миграции базы данных

Миграции базы данных выполняются через SQL скрипты, расположенные в директории `migrations/`.

## Структура

- `000_check_tables.sql` - вспомогательный скрипт для проверки существования таблиц
- `001_init_schema.sql` - первоначальная миграция с созданием всех таблиц

## Применение миграций

### Автоматическое применение

Миграции применяются автоматически при запуске приложения через функцию `init_db()` в `app/database.py`.

### Ручное применение

#### Вариант 1: Через Python скрипт

```bash
cd backend
python scripts/apply_migrations.py
```

#### Вариант 2: Через Docker Compose

```bash
docker compose exec rag-app python scripts/apply_migrations.py
```

#### Вариант 3: Прямое применение SQL

```bash
# Подключение к PostgreSQL контейнеру
docker compose exec postgres psql -U rag_user -d rag_db

# Или применение через psql из файла
docker compose exec -T postgres psql -U rag_user -d rag_db < migrations/001_init_schema.sql
```

## Создание новой миграции

1. Создайте новый файл в директории `migrations/` с номером следующей миграции:
   ```
   002_add_new_column.sql
   ```

2. Файлы миграций применяются в порядке сортировки имен файлов (алфавитно-цифровой порядок)

3. Включите в миграцию:
   - Проверки существования таблиц/колонок (`IF NOT EXISTS`)
   - Откат изменений (если необходимо)
   - Комментарии для документации

## Схема базы данных

Все таблицы создаются в схеме `oozo-schema`. Схема создается автоматически при применении миграции `001_init_schema.sql`.

## Структура таблиц

Все таблицы находятся в схеме `oozo-schema`:

### Таблица `oozo-schema.chunks`
Хранит чанки документов, используемые для создания векторной БД.

### Таблица `oozo-schema.query_logs`
Хранит логи запросов пользователей к системе.

### Таблица `oozo-schema.query_log_chunks`
Промежуточная таблица для связи many-to-many между `query_logs` и `chunks`.

## Проверка состояния миграций

Для проверки какие таблицы существуют в БД:

```bash
# Показать все таблицы в схеме oozo-schema
docker compose exec postgres psql -U rag_user -d rag_db -c "\dt oozo-schema.*"

# Показать все схемы
docker compose exec postgres psql -U rag_user -d rag_db -c "\dn"

# Или через скрипт проверки:
docker compose exec -T postgres psql -U rag_user -d rag_db < migrations/000_check_tables.sql
```

