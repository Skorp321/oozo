#!/bin/bash

# Скрипт для запуска Streamlit фронтенда

echo "🚀 Запуск Streamlit фронтенда..."

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверка наличия pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 не найден. Установите pip"
    exit 1
fi

# Проверка виртуального окружения
if [ -d "../.venv" ]; then
    echo "📦 Использование существующего виртуального окружения..."
    source ../.venv/bin/activate
    pip install -r requirements.txt
else
    echo "📦 Создание виртуального окружения..."
    python3 -m venv .venv
    source .venv/bin/activate
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