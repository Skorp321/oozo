#!/bin/bash
# Скрипт для запуска Streamlit фронтенда

cd "$(dirname "$0")"
export STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
streamlit run frontend/app.py
