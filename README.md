# RAG Oozo System

Полнофункциональная система RAG (Retrieval-Augmented Generation) с веб-интерфейсом для поиска и генерации ответов на основе документов.

## 🚀 Быстрый запуск

### Требования

- Docker и Docker Compose
- OpenAI API ключ

### Установка и запуск

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd rag_oozo
```

2. **Создайте файл переменных окружения:**
```bash
cp env.example .env
```

3. **Настройте OpenAI API ключ в `.env`:**
```env
OPENAI_API_KEY=your_openai_api_key_here
```

4. **Добавьте документы в папку `docs/`:**
```bash
# Поместите .docx файлы в папку docs/
cp your_documents/*.docx docs/
```

5. **Запустите систему:**
```bash
docker-compose up --build
```

6. **Откройте приложение:**
- Фронтенд: http://localhost:3000
- API документация: http://localhost:8000/docs
- Состояние системы: http://localhost:8000/health

## 🏗️ Архитектура

Система состоит из двух основных компонентов:

### Backend (FastAPI + LangChain + FAISS)
- **FastAPI** - веб-фреймворк для API
- **LangChain** - фреймворк для RAG пайплайнов
- **FAISS** - векторная база данных для поиска
- **HuggingFace Embeddings** - модель эмбеддингов multilingual-e5-large
- **OpenAI** - языковая модель для генерации ответов

### Frontend (React)
- **React** - пользовательский интерфейс
- **Современный UI** - красивый и отзывчивый дизайн
- **Чат интерфейс** - интуитивное взаимодействие с системой

## 📁 Структура проекта

```
rag_oozo/
├── backend/                 # FastAPI бэкенд
│   ├── app/
│   │   ├── api/            # API роутеры
│   │   ├── config.py       # Конфигурация
│   │   ├── schemas.py      # Pydantic модели
│   │   ├── rag_system.py   # Основная RAG система
│   │   └── document_processor.py  # Обработка документов
│   ├── scripts/            # CLI скрипты
│   ├── data/               # FAISS индекс
│   ├── main.py            # Точка входа
│   └── requirements.txt   # Python зависимости
├── frontend/               # React фронтенд
│   ├── src/
│   │   ├── components/    # React компоненты
│   │   ├── services/      # API сервисы
│   │   └── config/        # Конфигурация
│   └── package.json       # Node.js зависимости
├── docs/                   # Документы для индексации (.docx)
├── docker-compose.yml     # Docker конфигурация
└── README.md              # Документация
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENAI_API_KEY` | API ключ OpenAI | - |
| `EMBEDDING_MODEL_NAME` | Модель эмбеддингов | intfloat/multilingual-e5-large |
| `CHUNK_SIZE` | Размер чанка | 1000 |
| `CHUNK_OVERLAP` | Перекрытие чанков | 200 |
| `OPENAI_MODEL_NAME` | Модель OpenAI | gpt-3.5-turbo |
| `MAX_TOKENS` | Максимум токенов | 4000 |
| `TEMPERATURE` | Температура генерации | 0.7 |

## 📚 API Документация

### Основные эндпоинты

- `POST /api/query` - Обработка запроса пользователя
- `GET /health` - Проверка состояния системы
- `GET /api/stats` - Статистика коллекции документов
- `GET /api/info` - Информация о системе
- `POST /api/similarity` - Поиск похожих документов
- `POST /api/ingest` - Переиндексация документов

### Пример использования API

```bash
# Отправка запроса
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Что такое RAG?", "return_sources": true}'

# Проверка состояния
curl "http://localhost:8000/health"

# Получение статистики
curl "http://localhost:8000/api/stats"
```

## 🔄 Индексация документов

### Автоматическая индексация
Система автоматически индексирует документы при первом запуске.

### Ручная переиндексация
```bash
# Через API
curl -X POST "http://localhost:8000/api/ingest"

# Через CLI скрипт
docker exec rag-backend python scripts/ingest_documents.py --verbose
```

### Поддерживаемые форматы
- **.docx** - Microsoft Word документы

## 🎯 Использование

### Через веб-интерфейс
1. Откройте http://localhost:3000
2. Введите ваш вопрос в поле чата
3. Получите ответ с источниками

### Через API
```python
import requests

response = requests.post("http://localhost:8000/api/query", json={
    "question": "Ваш вопрос здесь",
    "return_sources": True
})

result = response.json()
print(f"Ответ: {result['answer']}")
print(f"Источники: {len(result['sources'])}")
```

## 🛠️ Разработка

### Локальная разработка

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm start
```

### Добавление новых функций

1. **Новые эндпоинты** - создайте роутер в `backend/app/api/`
2. **Новые форматы документов** - расширьте `document_processor.py`
3. **Новые модели** - обновите конфигурацию в `config.py`

## 🔍 Мониторинг и отладка

### Логи
```bash
# Просмотр логов бэкенда
docker logs rag-backend

# Просмотр логов фронтенда
docker logs rag-frontend

# Просмотр всех логов
docker-compose logs -f
```

### Проверка состояния
```bash
# Проверка здоровья системы
curl http://localhost:8000/health

# Статистика системы
curl http://localhost:8000/api/stats
```

## 🚨 Устранение неполадок

### Проблемы с OpenAI API
1. Проверьте правильность API ключа
2. Убедитесь в наличии средств на счете
3. Проверьте лимиты API

### Проблемы с индексацией
1. Убедитесь, что документы в формате .docx
2. Проверьте права доступа к папке docs/
3. Проверьте логи бэкенда

### Проблемы с памятью
1. Уменьшите размер чанков
2. Используйте более легкую модель эмбеддингов
3. Ограничьте количество документов

## 📈 Производительность

### Оптимизация
- Используйте SSD для хранения индекса
- Увеличьте RAM для больших коллекций
- Настройте размер чанков под ваши документы

### Масштабирование
- Используйте Redis для кэширования
- Разверните несколько экземпляров бэкенда
- Используйте балансировщик нагрузки

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

## 🆘 Поддержка

Если у вас возникли проблемы:
1. Проверьте раздел "Устранение неполадок"
2. Просмотрите логи системы
3. Создайте Issue в репозитории

---

**RAG Oozo System** - мощная система для работы с документами и генерации ответов на основе RAG технологии. 