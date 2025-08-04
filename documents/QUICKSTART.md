# 🚀 Быстрый запуск RAG Oozo System

## 📋 Требования

- Docker и Docker Compose
- OpenAI API ключ
- Минимум 4GB RAM
- 10GB свободного места на диске

## ⚡ Быстрый запуск (5 минут)

### 1. Подготовка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd rag_oozo

# Создайте файл переменных окружения
cp env.example .env
```

### 2. Настройка OpenAI API

Отредактируйте файл `.env`:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

Получите API ключ на [platform.openai.com](https://platform.openai.com/api-keys)

### 3. Добавление документов

Поместите ваши .docx файлы в папку `docs/`:
```bash
cp your_documents/*.docx docs/
```

### 4. Запуск системы

```bash
# Автоматический запуск с проверками
./start.sh

# Или вручную
docker-compose up --build -d
```

### 5. Проверка работы

Откройте в браузере:
- **Фронтенд**: http://localhost:3000
- **API документация**: http://localhost:8000/docs
- **Состояние системы**: http://localhost:8000/health

## 🎯 Первое использование

1. Откройте http://localhost:3000
2. Введите вопрос в поле чата
3. Получите ответ с источниками
4. Изучите найденные документы

## 🔧 Полезные команды

```bash
# Запуск системы
./start.sh

# Остановка системы
./stop.sh

# Просмотр логов
./logs.sh

# Переиндексация документов
./reindex.sh

# Проверка состояния
curl http://localhost:8000/health

# Статистика системы
curl http://localhost:8000/api/stats
```

## 🚨 Устранение проблем

### Система не запускается
```bash
# Проверьте логи
./logs.sh backend

# Проверьте Docker
docker ps

# Перезапустите
docker-compose down
docker-compose up --build
```

### Ошибки OpenAI API
1. Проверьте API ключ в `.env`
2. Убедитесь в наличии средств на счете
3. Проверьте лимиты API

### Документы не индексируются
```bash
# Проверьте формат файлов (.docx)
ls -la docs/

# Переиндексируйте
./reindex.sh

# Проверьте логи
./logs.sh backend
```

## 📊 Мониторинг

### Проверка состояния
```bash
# Здоровье системы
curl http://localhost:8000/health

# Статистика
curl http://localhost:8000/api/stats

# Информация о системе
curl http://localhost:8000/api/info
```

### Просмотр логов
```bash
# Все логи
./logs.sh

# Только бэкенд
./logs.sh backend

# Только фронтенд
./logs.sh frontend
```

## 🔄 Обновление документов

1. Добавьте новые .docx файлы в `docs/`
2. Запустите переиндексацию:
```bash
./reindex.sh
```

## 🛠️ Разработка

### Локальная разработка
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm start
```

### Добавление новых функций
1. Создайте ветку для новой функции
2. Внесите изменения
3. Протестируйте локально
4. Создайте Pull Request

## 📞 Поддержка

- 📖 Документация: README.md
- 🐛 Issues: GitHub Issues
- 💬 Обсуждения: GitHub Discussions

---

**Готово!** Ваша RAG система запущена и готова к использованию! 🎉 