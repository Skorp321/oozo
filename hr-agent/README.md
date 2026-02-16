# HR Agent с MCP сервером

HR агент с использованием Model Context Protocol (MCP) сервера, LangGraph React агента и Streamlit фронтенда.

## Архитектура

Система состоит из трех основных компонентов:

1. **MCP Server** (HTTP REST API) - предоставляет инструменты для RAG, персональных дней и отпусков
2. **LangGraph Agent** - React агент, использующий инструменты MCP сервера
3. **Streamlit Frontend** - пользовательский интерфейс

```
Frontend (Streamlit) 
    ↓ HTTP
LangGraph Agent 
    ↓ HTTP (MCP Protocol)
MCP Server 
    ↓
Backend (RAG, HR Data)
```

## Структура проекта

```
hr-agent/
├── mcp_server/              # MCP сервер на FastAPI
│   ├── server.py            # Основной FastAPI сервер
│   ├── schemas.py           # Pydantic схемы
│   └── tools/               # Инструменты MCP
│       ├── tool_base.py     # Базовый класс инструментов
│       ├── rag_tool.py      # RAG инструмент
│       └── leave_tool.py    # Инструменты для отпусков
├── backend/                 # Бизнес-логика
│   ├── config.py            # Конфигурация
│   ├── hr_data.py           # Мок-данные сотрудников
│   ├── rag_system.py        # RAG система
│   └── document_processor.py # Обработка документов
├── agent/                   # LangGraph React агент
│   ├── graph.py             # Определение графа агента
│   └── tools.py             # Обертки для MCP инструментов
├── frontend/                # Streamlit фронтенд
│   └── app.py               # Основное приложение
├── requirements.txt         # Зависимости
├── .env.example            # Пример переменных окружения
└── README.md               # Документация
```

## Установка

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

3. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

4. Настройте переменные окружения в `.env`:
- `OPENAI_API_KEY` - ключ для LLM API
- `OPENAI_API_BASE` - базовый URL для LLM API
- `DOCS_PATH` - путь к документам для RAG
- `INDEX_PATH` - путь к FAISS индексу

## Запуск

### 1. Запуск MCP сервера

```bash
cd hr-agent
python -m mcp_server.server
```

Сервер будет доступен по адресу `http://localhost:8001`

### 2. Запуск Streamlit фронтенда

```bash
cd hr-agent
streamlit run frontend/app.py
```

Фронтенд будет доступен по адресу `http://localhost:8501`

## Использование

### Доступные инструменты

1. **RAG Query** (`rag_query`)
   - Поиск информации в документах
   - Параметры: `{"query": "ваш вопрос"}`

2. **Get Personal Days** (`get_personal_days`)
   - Получение персональных дней отпуска
   - Параметры: `{"employee_name": "alice"}`

3. **Get Remaining Vacation Days** (`get_remaining_vacation_days`)
   - Получение оставшихся дней отпуска
   - Параметры: `{"employee_name": "alice"}`

### Примеры запросов

- "Сколько персональных дней у alice?"
- "Сколько осталось дней отпуска у bob?"
- "Найди информацию о политике отпусков"

## API MCP сервера

### Список инструментов
```bash
POST /mcp/tools/list
```

### Вызов инструмента
```bash
POST /mcp/tools/call
Content-Type: application/json

{
  "name": "rag_query",
  "arguments": {
    "query": "ваш вопрос"
  }
}
```

### Проверка здоровья
```bash
GET /health
```

## Конфигурация

Основные переменные окружения:

- `OPENAI_API_KEY` - ключ для LLM API
- `OPENAI_API_BASE` - базовый URL для LLM API
- `OPENAI_MODEL_NAME` - название модели LLM
- `EMBEDDING_MODEL_NAME` - название модели эмбеддингов
- `EMBEDDING_API_BASE` - базовый URL для API эмбеддингов
- `DOCS_PATH` - путь к документам для RAG
- `INDEX_PATH` - путь к FAISS индексу
- `MCP_SERVER_PORT` - порт MCP сервера (по умолчанию 8001)
- `TEMPERATURE` - температура для LLM (по умолчанию 0.1)

## Разработка

### Структура инструментов

Каждый инструмент должен наследоваться от `MCPTool` и реализовывать:
- `name` - имя инструмента
- `description` - описание инструмента
- `input_schema` - JSON Schema для входных параметров
- `execute()` - метод выполнения инструмента

### Добавление нового инструмента

1. Создайте новый класс в `mcp_server/tools/`
2. Наследуйтесь от `MCPTool`
3. Реализуйте необходимые методы
4. Зарегистрируйте инструмент в `mcp_server/server.py`

## Лицензия

MIT
