# Инструкция по запуску Frontend и Backend на одной машине без Docker

## Обзор

Данная инструкция описывает процесс настройки и запуска приложения RAG Oozo System на одной машине без использования Docker. Приложение состоит из двух частей:
- **Backend** - FastAPI сервер на Python (порт 8008)
- **Frontend** - React приложение (порт 3000)

## Предварительные требования

### Системные требования
- Python 3.8+ 
- Node.js 16+ и npm
- Минимум 4GB RAM (для работы с моделями машинного обучения)
- 2GB свободного места на диске

### Установка зависимостей системы

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm
```

#### CentOS/RHEL:
```bash
sudo yum install python3 python3-pip nodejs npm
```

## Шаг 1: Настройка Backend

### 1.1 Переход в директорию backend
```bash
cd backend
```

### 1.2 Создание виртуального окружения Python
```bash
python3 -m venv venv
source venv/bin/activate  # Для Linux/Mac
# или
venv\Scripts\activate     # Для Windows
```

### 1.3 Установка зависимостей Python
```bash
pip install -r requirements.txt
```

### 1.4 Настройка переменных окружения
```bash
cp env.example .env
```

Отредактируйте файл `.env`:
```bash
nano .env
```

Убедитесь, что в файле указаны правильные значения:
```env
# OpenAI API Configuration
OPENAI_API_KEY=your_actual_openai_api_key_here

# Embedding Model Configuration
EMBEDDING_MODEL_NAME=./models/multilingual-e5-large

# File Paths
DOCS_PATH=../docs
INDEX_PATH=./data/faiss_index

# Document Processing Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# OpenAI Model Configuration
OPENAI_MODEL_NAME=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7

# API Configuration
HOST=0.0.0.0
PORT=8008
DEBUG=false
```

### 1.5 Скачивание модели для эмбеддингов
```bash
# Создание директории для моделей
mkdir -p models

# Скачивание модели (может занять время)
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-large')
model.save('./models/multilingual-e5-large')
"
```

### 1.6 Создание индекса документов (опционально)
```bash
python scripts/ingest_documents.py
```

### 1.7 Запуск backend сервера
```bash
# В виртуальном окружении
uvicorn main:app --host 0.0.0.0 --port 8008 --reload
```

Backend будет доступен по адресу: http://localhost:8008

## Шаг 2: Настройка Frontend

### 2.1 Переход в директорию frontend
```bash
cd ../frontend
```

### 2.2 Установка зависимостей Node.js
```bash
npm install
```

### 2.3 Настройка конфигурации для локального запуска

#### Вариант A: Использование прокси (рекомендуется для разработки)

В файле `package.json` уже настроен прокси на `http://10.77.160.35:8000`. Измените его на localhost:

```json
{
  "proxy": "http://localhost:8008"
}
```

#### Вариант B: Настройка через переменные окружения

Создайте файл `.env` в директории frontend:
```bash
echo "REACT_APP_API_BASE_URL=http://localhost:8008" > .env
```

### 2.4 Запуск frontend в режиме разработки
```bash
npm start
```

Frontend будет доступен по адресу: http://localhost:3000

## Шаг 3: Проверка работоспособности

### 3.1 Проверка backend
```bash
curl http://localhost:8008/
curl http://localhost:8008/health
```

### 3.2 Проверка frontend
Откройте браузер и перейдите на http://localhost:3000

### 3.3 Проверка взаимодействия
В интерфейсе frontend попробуйте отправить сообщение - оно должно обработаться backend'ом.

## Шаг 4: Запуск в продакшн режиме

### 4.1 Сборка frontend
```bash
cd frontend
npm run build
```

### 4.2 Запуск frontend в продакшн режиме
```bash
npm run serve
```

### 4.3 Запуск backend в продакшн режиме
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8008
```

## Возможные проблемы и решения

### Проблема: Frontend не может подключиться к backend

**Решение:**
1. Убедитесь, что backend запущен на порту 8008
2. Проверьте настройки CORS в `backend/main.py`
3. Убедитесь, что прокси настроен правильно в `frontend/package.json`

### Проблема: Ошибка "Module not found" при запуске backend

**Решение:**
1. Убедитесь, что виртуальное окружение активировано
2. Переустановите зависимости: `pip install -r requirements.txt`

### Проблема: Модель не загружается

**Решение:**
1. Убедитесь, что модель скачана в директорию `backend/models/`
2. Проверьте путь к модели в `.env` файле
3. Убедитесь, что достаточно места на диске

### Проблема: Порт 3000 занят

**Решение:**
```bash
# Найти процесс, использующий порт 3000
lsof -i :3000

# Завершить процесс
kill -9 <PID>

# Или запустить на другом порту
PORT=3001 npm start
```

### Проблема: Порт 8008 занят

**Решение:**
```bash
# Найти процесс, использующий порт 8008
lsof -i :8008

# Завершить процесс
kill -9 <PID>

# Или запустить на другом порту
uvicorn main:app --host 0.0.0.0 --port 8009
```

## Автоматизация запуска

### Создание скрипта запуска

Создайте файл `start_local.sh` в корневой директории проекта:

```bash
#!/bin/bash

# Запуск backend
echo "Запуск backend..."
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8008 --reload &
BACKEND_PID=$!

# Ожидание запуска backend
sleep 5

# Запуск frontend
echo "Запуск frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "Приложение запущено!"
echo "Backend: http://localhost:8008"
echo "Frontend: http://localhost:3000"
echo "Для остановки нажмите Ctrl+C"

# Ожидание сигнала завершения
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
```

Сделайте скрипт исполняемым:
```bash
chmod +x start_local.sh
```

Запуск:
```bash
./start_local.sh
```

## Мониторинг и логи

### Просмотр логов backend
```bash
# В терминале с запущенным backend
# Логи выводятся автоматически

# Или перенаправление в файл
uvicorn main:app --host 0.0.0.0 --port 8008 > backend.log 2>&1
```

### Просмотр логов frontend
```bash
# В терминале с запущенным frontend
# Логи выводятся автоматически

# Или перенаправление в файл
npm start > frontend.log 2>&1
```

## Заключение

После выполнения всех шагов у вас должно быть работающее приложение с:
- Backend API на http://localhost:8008
- Frontend интерфейс на http://localhost:3000
- Полноценное взаимодействие между компонентами

Для остановки приложения используйте Ctrl+C в терминалах с запущенными сервисами. 