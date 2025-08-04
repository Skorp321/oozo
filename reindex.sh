#!/bin/bash

# RAG Oozo System - Reindex Documents Script

echo "🔄 Переиндексация документов..."

# Проверка, запущена ли система
if ! docker ps | grep -q "rag-backend"; then
    echo "❌ Система не запущена. Запустите сначала: ./start.sh"
    exit 1
fi

echo "📋 Текущие документы в папке docs/:"
ls -la docs/ 2>/dev/null || echo "Папка docs/ пуста"

echo ""
echo "🔄 Запуск переиндексации..."

# Выполнение переиндексации через API
response=$(curl -s -X POST http://localhost:8000/api/ingest)

if [ $? -eq 0 ]; then
    echo "✅ Переиндексация завершена успешно"
    echo "📊 Результат:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "❌ Ошибка при переиндексации"
    echo "📋 Логи бэкенда:"
    docker logs rag-backend --tail 10
fi

echo ""
echo "📊 Статистика системы:"
curl -s http://localhost:8000/api/stats | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/api/stats 