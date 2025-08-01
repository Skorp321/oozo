# RAG System - Система поиска с дополненной генерацией

Это система RAG (Retrieval-Augmented Generation), построенная с использованием Python, PostgreSQL с pgvector, и React.

## 🚀 Быстрый запуск

### Предварительные требования
- Docker и Docker Compose
- API ключ от Mistral AI

### Установка

1. Клонируйте репозиторий и перейдите в директорию проекта

2. **КРИТИЧЕСКИ ВАЖНО**: Создайте файл `.env` в корне проекта со следующим содержимым:
```bash
# ОБЯЗАТЕЛЬНО: Замените на ваш реальный API ключ от Mistral AI
MISTRAL_API_KEY=your_actual_mistral_api_key_here

# Остальные настройки (по желанию)
DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@postgres-pgvector:5432/rag_db
EMBEDDING_MODEL_NAME=intfloat/e5-base-v2
LLM_MODEL_NAME=mistral-small
CHUNK_SIZE=512
CHUNK_OVERLAP=64
LOG_LEVEL=INFO
```

3. Получите API ключ Mistral:
   - Перейдите на [https://console.mistral.ai/](https://console.mistral.ai/)
   - Создайте аккаунт или войдите в систему
   - Создайте новый API ключ
   - Скопируйте ключ и замените `your_actual_mistral_api_key_here` в файле `.env`

4. Запустите систему:
```bash
docker compose up --build -d
```

5. Откройте браузер и перейдите по адресу:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API документация: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 🔧 Исправленные проблемы

### 1. ❌ Проблема: docker-compose не найден
**Решение:** Использована команда `docker compose` вместо устаревшей `docker-compose`

### 2. ❌ Проблема: Ошибки проксирования в frontend
**Исходная ошибка:**
```
Proxy error: Could not proxy request /health from localhost:3000 to http://localhost:8000
```
**Решение:** Изменен прокси в `frontend/package.json` с `http://localhost:8000` на `http://rag-app:8000` для корректной работы в Docker-сети

### 3. ❌ Проблема: Устаревшие импорты LangChain
**Исходные предупреждения:**
```
LangChainDeprecationWarning: Importing LLMs from langchain is deprecated
LangChainDeprecationWarning: The class `HuggingFaceEmbeddings` was deprecated
```
**Решение:** 
- Обновлен `requirements.txt` с добавлением `langchain-huggingface`
- Изменен импорт с `from langchain_community.embeddings import HuggingFaceEmbeddings` на `from langchain_huggingface import HuggingFaceEmbeddings`
- Убран устаревший импорт `from langchain.llms import OpenAI`

### 4. ❌ Проблема: Несовместимость с новым langchain_postgres
**Исходная ошибка:**
```
TypeError: PGVector.__init__() got an unexpected keyword argument 'connection_string'
```
**Решение:** Возвращен к стабильному импорту `from langchain_community.vectorstores import PGVector`

### 5. ❌ Проблема: Ошибки подключения к PostgreSQL
**Исходная ошибка:**
```
FATAL: database "rag_user" does not exist
```
**Решение:** Исправлен healthcheck в `docker-compose.yml` - добавлен параметр `-d rag_db` к команде `pg_isready`

### 6. ❌ Проблема: Отсутствие MISTRAL_API_KEY
**Исходное предупреждение:**
```
WARN[0000] The "MISTRAL_API_KEY" variable is not set. Defaulting to a blank string.
```
**Решение:** 
- Добавлен импорт `from dotenv import load_dotenv` в `config/settings.py`
- Добавлена переменная `MISTRAL_API_KEY` в настройки
- Обновлен `docker-compose.yml` для передачи переменной в контейнер
- Создан файл `.env` в корне проекта для хранения API ключа

## 📋 Компоненты системы

- **PostgreSQL с pgvector**: База данных для хранения векторных представлений
- **RAG Backend**: Python FastAPI приложение с LangChain
- **React Frontend**: Современный веб-интерфейс для чата
- **Mistral AI**: LLM для генерации ответов

## 🔍 API Endpoints

- `GET /health` - Проверка состояния системы  
- `POST /api/query` - Основной endpoint для вопросов
- `GET /api/stats` - Статистика векторного хранилища
- `POST /api/similarity` - Поиск по сходству
- `GET /docs` - Автоматическая документация API

## 🩺 Диагностика и устранение ошибок

### ❌ HTTP 500 Error - "Health check failed"

**Причина:** Отсутствует или некорректный MISTRAL_API_KEY

**Диагностика:**
```bash
# Проверьте статус контейнеров
docker compose ps

# Проверьте логи
docker compose logs rag-app

# Проверьте health endpoint
curl http://localhost:8000/health
```

**Решение:**
1. Убедитесь, что файл `.env` создан в корне проекта
2. Проверьте, что MISTRAL_API_KEY установлен корректно
3. Получите валидный API ключ на https://console.mistral.ai/
4. Перезапустите контейнеры: `docker compose restart`

### ❌ Database Connection Errors

**Симптомы:** Ошибки подключения к PostgreSQL

**Диагностика:**
```bash
# Проверьте состояние БД
docker compose ps postgres-pgvector

# Проверьте логи БД
docker compose logs postgres-pgvector

# Проверьте подключение
docker compose exec postgres-pgvector pg_isready -U rag_user -d rag_db
```

**Решение:**
1. Подождите полной инициализации БД (может занять 1-2 минуты)
2. Проверьте наличие volume для данных: `docker volume ls`
3. При необходимости пересоздайте контейнеры: `docker compose down && docker compose up -d`

### ❌ Frontend показывает "Система недоступна"

**Диагностика:**
1. Откройте DevTools в браузере (F12)
2. Проверьте вкладку Network на наличие ошибок
3. Посетите http://localhost:8000/health напрямую

**Решение:**
1. Убедитесь, что backend запущен: `docker compose ps rag-app`
2. Проверьте, что порт 8000 не занят другим процессом
3. Проверьте логи: `docker compose logs rag-app`

### ❌ Model Loading Errors

**Симптомы:** Ошибки загрузки embedding моделей

**Решение:**
1. Проверьте интернет соединение
2. Увеличьте timeout в docker-compose.yml
3. Система автоматически попробует fallback модель
4. Очистите cache моделей: `docker volume rm one_model_cache`

### 🔍 Команды для мониторинга

```bash
# Просмотр статуса всех сервисов
docker compose ps

# Просмотр логов в реальном времени
docker compose logs -f

# Просмотр использования ресурсов
docker stats

# Проверка health check
curl -s http://localhost:8000/health | jq

# Перезапуск конкретного сервиса
docker compose restart rag-app

# Полная пересборка
docker compose down && docker compose up --build -d
```

### 🛠️ Режимы работы системы

1. **Full Mode**: Все компоненты работают (API ключ установлен, БД доступна)
2. **Limited Mode**: Только поиск (БД работает, но нет API ключа)
3. **Debug Mode**: Только диагностика (система недоступна)

### 📊 Health Check Endpoint

Посетите http://localhost:8000/health для получения детальной информации о состоянии системы:

- `status`: общий статус (`ok`, `degraded`, `error`)
- `components`: состояние отдельных компонентов
- `issues`: список проблем
- `recommendations`: рекомендации по устранению

### 🆘 Получение помощи

Если проблемы persist:

1. Соберите диагностическую информацию:
```bash
# Создайте файл с диагностикой
echo "=== System Info ===" > debug.log
docker compose ps >> debug.log
echo -e "\n=== Health Check ===" >> debug.log
curl -s http://localhost:8000/health >> debug.log
echo -e "\n=== Logs ===" >> debug.log
docker compose logs --tail=50 >> debug.log
```

2. Проверьте переменные окружения
3. Убедитесь, что все порты свободны
4. Попробуйте полную пересборку: `docker compose down -v && docker compose up --build`

## 📝 Примечания

- **КРИТИЧЕСКИ ВАЖНО**: Система не будет работать без валидного MISTRAL_API_KEY
- Для получения API ключа Mistral посетите: https://console.mistral.ai/
- Система автоматически загружает документы из папки `rad_project/documents/`
- Все предупреждения об устаревших функциях LangChain устранены
- Frontend показывает детальную информацию об ошибках и рекомендации по их устранению
- Health check endpoint обновляется каждые 30 секунд
- Система поддерживает graceful degradation при частичных сбоях 