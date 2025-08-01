#!/bin/bash

# Скрипт для управления Docker контейнером RAG Chat Frontend

CONTAINER_NAME="rag-chat-frontend-container"
IMAGE_NAME="rag-chat-frontend"
PORT="3000"

case "$1" in
    "start")
        echo "Запуск контейнера $CONTAINER_NAME..."
        docker run -d -p $PORT:3000 --name $CONTAINER_NAME $IMAGE_NAME
        echo "Контейнер запущен! Приложение доступно по адресу: http://localhost:$PORT"
        ;;
    "stop")
        echo "Остановка контейнера $CONTAINER_NAME..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        echo "Контейнер остановлен и удален."
        ;;
    "restart")
        echo "Перезапуск контейнера $CONTAINER_NAME..."
        docker stop $CONTAINER_NAME 2>/dev/null
        docker rm $CONTAINER_NAME 2>/dev/null
        docker run -d -p $PORT:3000 --name $CONTAINER_NAME $IMAGE_NAME
        echo "Контейнер перезапущен! Приложение доступно по адресу: http://localhost:$PORT"
        ;;
    "logs")
        echo "Показ логов контейнера $CONTAINER_NAME..."
        docker logs -f $CONTAINER_NAME
        ;;
    "status")
        echo "Статус контейнера $CONTAINER_NAME:"
        docker ps -a | grep $CONTAINER_NAME
        ;;
    "build")
        echo "Сборка образа $IMAGE_NAME..."
        docker build -t $IMAGE_NAME .
        echo "Образ собран успешно!"
        ;;
    "shell")
        echo "Подключение к контейнеру $CONTAINER_NAME..."
        docker exec -it $CONTAINER_NAME /bin/sh
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|logs|status|build|shell}"
        echo ""
        echo "Команды:"
        echo "  start   - Запустить контейнер"
        echo "  stop    - Остановить и удалить контейнер"
        echo "  restart - Перезапустить контейнер"
        echo "  logs    - Показать логи контейнера"
        echo "  status  - Показать статус контейнера"
        echo "  build   - Собрать Docker образ"
        echo "  shell   - Подключиться к контейнеру через shell"
        echo ""
        echo "После запуска приложение будет доступно по адресу: http://localhost:$PORT"
        ;;
esac 