#!/bin/bash
# Применение миграций к PostgreSQL.
#
# Локально (нужен доступ к БД, в .env — POSTGRES_HOST=localhost и т.д.):
#   ./apply_migrations.sh
#   ./apply_migrations.sh local
#
# Через Docker (миграции выполняет контейнер rag-app):
#   ./apply_migrations.sh docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"

run_local() {
    echo "Применение миграций (локально)..."
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        set -a
        source "${SCRIPT_DIR}/.env"
        set +a
    fi
    cd "${BACKEND_DIR}"
    export PYTHONPATH="${BACKEND_DIR}"
    python scripts/apply_migrations.py
}

run_docker() {
    echo "Применение миграций через Docker (rag-app)..."
    docker compose -f "${SCRIPT_DIR}/docker-compose.yml" exec rag-app python scripts/apply_migrations.py
}

case "${1:-local}" in
    local)
        run_local
        ;;
    docker)
        run_docker
        ;;
    -h|--help)
        echo "Использование: $0 [local|docker]"
        echo "  local  — применить миграции локально (по умолчанию), читает .env из корня проекта"
        echo "  docker — применить миграции внутри контейнера rag-app"
        exit 0
        ;;
    *)
        echo "Неизвестный режим: $1. Используйте: $0 --help"
        exit 1
        ;;
esac

echo "Готово."
