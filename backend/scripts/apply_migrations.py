#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных
Использование: python scripts/apply_migrations.py
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import run_migrations, get_migration_files
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """
    Главная функция для применения миграций
    """
    logger.info("Запуск применения миграций...")
    logger.info(f"База данных: {settings.database_url}")
    
    migration_files = get_migration_files()
    
    if not migration_files:
        logger.warning("Миграции не найдены!")
        return
    
    logger.info(f"Найдено миграций: {len(migration_files)}")
    for mf in migration_files:
        logger.info(f"  - {mf.name}")
    
    try:
        run_migrations()
        logger.info("Все миграции успешно применены!")
    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



