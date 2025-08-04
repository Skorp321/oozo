FROM python:3.11-slim  
# nvidia/cuda:12.6.2-base-ubuntu22.04

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя без root прав
RUN useradd --create-home --shell /bin/bash app

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p data && chown -R app:app /app

# Переключение на пользователя app
USER app

# Открытие порта
EXPOSE 8000

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 