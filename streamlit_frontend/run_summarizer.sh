#!/bin/bash

# Скрипт для запуска сервиса суммаризации встреч

echo "🚀 Запуск сервиса суммаризации встреч..."
echo ""

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверяем наличие pip
if ! command -v pip &> /dev/null; then
    echo "❌ pip не найден. Установите pip"
    exit 1
fi

# Проверяем наличие файла requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ Файл requirements.txt не найден"
    exit 1
fi

# Проверяем наличие основного скрипта
if [ ! -f "meeting_summarizer.py" ]; then
    echo "❌ Файл meeting_summarizer.py не найден"
    exit 1
fi

# Проверяем наличие секретов
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  Файл .streamlit/secrets.toml не найден"
    echo "Создайте файл .streamlit/secrets.toml и добавьте ваш API ключ OpenAI:"
    echo "OPENAI_API_KEY = \"your-api-key-here\""
    echo ""
fi

echo "📦 Установка зависимостей..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Зависимости установлены успешно"
    echo ""
    echo "🌐 Запуск Streamlit сервиса..."
    echo "Сервис будет доступен по адресу: http://localhost:8501"
    echo "Для остановки нажмите Ctrl+C"
    echo ""
    
    # Запускаем Streamlit
    streamlit run meeting_summarizer.py
else
    echo "❌ Ошибка при установке зависимостей"
    exit 1
fi
