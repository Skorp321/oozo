#!/bin/bash

# Скрипт для запуска Streamlit фронтенда с существующим виртуальным окружением

echo "🚀 Запуск Streamlit фронтенда с виртуальным окружением..."

# Проверка наличия виртуального окружения
if [ ! -d "../.venv" ]; then
    echo "❌ Виртуальное окружение не найдено в родительской папке"
    echo "📝 Создайте виртуальное окружение: python3 -m venv .venv"
    echo "📝 Активируйте его: source .venv/bin/activate"
    echo "📝 Установите зависимости: pip install -r requirements.txt"
    exit 1
fi

# Активация виртуального окружения
echo "📦 Активация виртуального окружения..."
source ../.venv/bin/activate

# Проверка установки зависимостей
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Установка зависимостей..."
    pip install -r requirements.txt
fi

# Создание конфигурационной папки
mkdir -p .streamlit

# Создание файла secrets.toml если его нет
if [ ! -f .streamlit/secrets.toml ]; then
    echo "🔧 Создание конфигурационного файла..."
    cat > .streamlit/secrets.toml << EOF
# Конфигурация API
API_BASE_URL = "http://localhost:8000"
EOF
    echo "✅ Файл .streamlit/secrets.toml создан"
fi

# Запуск приложения
echo "🌐 Запуск Streamlit приложения на http://localhost:8501"
echo "📝 Для остановки нажмите Ctrl+C"
echo ""

streamlit run app.py --server.port=8501 --server.address=0.0.0.0 