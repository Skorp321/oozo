# Система логирования вопросов и ответов

## Обзор

Система автоматически логирует все вопросы пользователей и соответствующие ответы в JSONL файл для анализа и отладки.

## Файлы логов

Логи сохраняются в файл `./data/logs/qa_logs.jsonl` (по умолчанию). Путь можно изменить через переменную окружения `LOGS_PATH`.

## Формат логов

Каждая запись в логе содержит:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "type": "regular|stream",
  "request": {
    "question": "Вопрос пользователя",
    "return_sources": true
  },
  "response": {
    "answer": "Ответ системы",
    "sources_count": 3
  },
  "processing_time_seconds": 2.45,
  "error": null,
  "status": "success|error"
}
```

### Поля:

- `timestamp` - время запроса в ISO формате
- `type` - тип запроса: "regular" для обычных запросов, "stream" для потоковых
- `request` - информация о запросе
  - `question` - вопрос пользователя
  - `return_sources` - запрашивались ли источники
- `response` - информация об ответе
  - `answer` - полный ответ системы
  - `sources_count` - количество найденных источников
- `processing_time_seconds` - время обработки в секундах
- `error` - сообщение об ошибке (если есть)
- `status` - статус обработки: "success" или "error"

## API эндпоинты

### Получение логов

```
GET /api/logs?limit=100
```

Параметры:
- `limit` - максимальное количество записей (по умолчанию 100)

### Очистка логов

```
DELETE /api/logs
```

## Скрипт для просмотра логов

Используйте скрипт `scripts/view_logs.py` для удобного просмотра логов:

```bash
# Просмотр последних 50 записей
python scripts/view_logs.py

# Просмотр последних 100 записей
python scripts/view_logs.py --limit 100

# Просмотр только ошибок
python scripts/view_logs.py --errors-only

# Просмотр логов из другого файла
python scripts/view_logs.py --file /path/to/logs.jsonl
```

## Настройка

### Переменные окружения

- `LOGS_PATH` - путь к файлу логов (по умолчанию: `./data/logs/qa_logs.jsonl`)

### Пример .env файла

```env
LOGS_PATH=./data/logs/qa_logs.jsonl
```

## Автоматическое логирование

Система автоматически логирует:

1. **Обычные запросы** (`POST /api/query`) - полный вопрос и ответ
2. **Потоковые запросы** (`POST /api/query/stream`) - вопрос и собранный ответ
3. **Ошибки** - вопросы с пустыми ответами и описанием ошибки

## Ротация логов

Для продакшена рекомендуется настроить ротацию логов. Можно использовать:

- `logrotate` для автоматической ротации
- Внешние системы логирования (ELK, Graylog и т.д.)

## Безопасность

⚠️ **Важно**: Логи содержат пользовательские данные. Обеспечьте:

1. Ограниченный доступ к файлам логов
2. Шифрование чувствительных данных
3. Регулярную очистку старых логов
4. Соответствие требованиям GDPR/законодательства

## Примеры использования

### Анализ производительности

```python
import json
from datetime import datetime, timedelta

# Анализ времени ответа за последние 24 часа
with open('data/logs/qa_logs.jsonl', 'r') as f:
    logs = [json.loads(line) for line in f]

yesterday = datetime.now() - timedelta(days=1)
recent_logs = [
    log for log in logs 
    if datetime.fromisoformat(log['timestamp']) > yesterday
]

avg_time = sum(log['processing_time_seconds'] for log in recent_logs) / len(recent_logs)
print(f"Среднее время ответа: {avg_time:.2f} сек")
```

### Поиск ошибок

```bash
# Поиск ошибок за последние 24 часа
python scripts/view_logs.py --errors-only --limit 1000 | grep "$(date -d '24 hours ago' +%Y-%m-%d)"
```
