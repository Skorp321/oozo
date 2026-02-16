#!/bin/bash
# Скрипт для остановки контейнеров и исправления Docker

echo "=== Остановка контейнеров Docker ==="

# Вариант 1: Перезапуск snap docker (исправит права на сокет)
echo "1. Перезапуск snap docker..."
sudo snap restart docker
sleep 3

# Пробуем остановить контейнеры
echo "2. Останавливаем контейнеры..."
cd /home/skorp321/Projects/SBL/one
docker-compose down

# Если не помогло, останавливаем системный docker (конфликтует со snap)
echo "3. Останавливаем системный Docker..."
sudo systemctl stop docker.socket docker.service
sudo systemctl disable docker.socket docker.service

# Ещё раз пробуем
echo "4. Повторная попытка остановить контейнеры..."
docker-compose down

echo "=== Готово ==="
docker ps -a | grep -E "rag|streamlit" || echo "Контейнеры успешно остановлены!"
