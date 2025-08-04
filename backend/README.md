# RAG Oozo Backend

Бэкенд система для RAG (Retrieval-Augmented Generation) приложения, построенная на FastAPI с использованием LangChain и FAISS.

## Архитектура

Система состоит из следующих компонентов:

- **FastAPI** - веб-фреймворк для API
- **LangChain** - фреймворк для RAG пайплайнов
- **FAISS** - векторная база данных для поиска
- **HuggingFace Embeddings** - модель эмбеддингов multilingual-e5-large
- **OpenAI** - языковая модель для генерации ответов

## Установка и запуск

### Локальная разработка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `env.example`:
```bash
cp env.example .env
```

4. Настройте переменные окружения в `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
DOCS_PATH=../docs
INDEX_PATH=./data/faiss_index
```

5. Запустите сервер:
```bash
uvicorn main:app --reload
```

### Docker

1. Соберите образ:
```bash
docker build -t rag-backend .
```

2. Запустите контейнер:
```bash
docker run -p 8000:8000 --env-file .env rag-backend
```

## API Эндпоинты

### Чат API

- `POST /api/query` - Обработка запроса пользователя
  - Body: `{"question": "текст вопроса", "return_sources": true}`
  - Response: `{"question": "...", "answer": "...", "sources": [...]}`

### Системные API

- `GET /health` - Проверка состояния системы
- `GET /api/info` - Информация о системе
- `GET /api/stats` - Статистика коллекции документов
- `POST /api/similarity` - Поиск похожих документов
- `POST /api/ingest` - Переиндексация документов
- `GET /api/documents` - Список доступных документов

## Индексация документов

### Автоматическая индексация

Система автоматически индексирует документы при запуске, если индекс не существует.

### Ручная индексация

Используйте CLI скрипт для индексации:

```bash
python scripts/ingest_documents.py --docs-path ../docs --verbose
```

### API индексация

Отправьте POST запрос к `/api/ingest` для переиндексации документов.

## Конфигурация

### Переменные окружения

- `OPENAI_API_KEY` - API ключ OpenAI (обязательно)
- `EMBEDDING_MODEL_NAME` - Модель эмбеддингов (по умолчанию: intfloat/multilingual-e5-large)
- `DOCS_PATH` - Путь к папке с документами (по умолчанию: ../docs)
- `INDEX_PATH` - Путь для сохранения FAISS индекса (по умолчанию: ./data/faiss_index)
- `CHUNK_SIZE` - Размер чанка в символах (по умолчанию: 1000)
- `CHUNK_OVERLAP` - Перекрытие между чанками (по умолчанию: 200)
- `OPENAI_MODEL_NAME` - Модель OpenAI (по умолчанию: gpt-3.5-turbo)
- `MAX_TOKENS` - Максимальное количество токенов (по умолчанию: 4000)
- `TEMPERATURE` - Температура генерации (по умолчанию: 0.7)

## Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # Конфигурация
│   ├── schemas.py         # Pydantic модели
│   ├── rag_system.py      # Основная RAG система
│   ├── document_processor.py  # Обработка документов
│   └── api/
│       ├── __init__.py
│       ├── chat.py        # Чат API
│       └── system.py      # Системные API
├── scripts/
│   └── ingest_documents.py  # CLI для индексации
├── data/                  # FAISS индекс и метаданные
├── main.py               # Точка входа FastAPI
├── requirements.txt      # Python зависимости
├── Dockerfile           # Docker конфигурация
└── README.md           # Документация
```

## Логирование

Система использует стандартное логирование Python. Логи включают:

- Инициализацию системы
- Обработку документов
- Выполнение запросов
- Ошибки и предупреждения

## Мониторинг

### Проверка состояния

```bash
curl http://localhost:8000/health
```

### Статистика системы

```bash
curl http://localhost:8000/api/stats
```

## Примеры использования

### Отправка запроса

```python
import requests

response = requests.post("http://localhost:8000/api/query", json={
    "question": "Что такое RAG система?",
    "return_sources": True
})

result = response.json()
print(f"Ответ: {result['answer']}")
print(f"Источники: {len(result['sources'])}")
```

### Поиск похожих документов

```python
response = requests.post("http://localhost:8000/api/similarity", json={
    "query": "векторные базы данных",
    "top_k": 3
})

results = response.json()
for result in results['results']:
    print(f"Документ: {result['title']}")
    print(f"Содержание: {result['content'][:100]}...")
    print(f"Схожесть: {result['score']}")
```

## Устранение неполадок

### Проблемы с OpenAI API

1. Проверьте правильность API ключа
2. Убедитесь, что у вас есть доступ к выбранной модели
3. Проверьте лимиты API

### Проблемы с индексацией

1. Убедитесь, что папка с документами существует
2. Проверьте, что документы имеют формат .docx
3. Проверьте права доступа к папкам

### Проблемы с памятью

1. Уменьшите размер чанков
2. Используйте более легкую модель эмбеддингов
3. Ограничьте количество документов

## Разработка

### Добавление новых эндпоинтов

1. Создайте новый роутер в `app/api/`
2. Добавьте схемы в `app/schemas.py`
3. Подключите роутер в `main.py`

### Изменение модели эмбеддингов

1. Обновите `EMBEDDING_MODEL_NAME` в конфигурации
2. Переиндексируйте документы
3. Проверьте совместимость размерности векторов

### Добавление новых форматов документов

1. Расширьте `document_processor.py`
2. Добавьте новые функции извлечения текста
3. Обновите логику загрузки документов 