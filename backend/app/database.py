import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Создание движка SQLAlchemy
# Устанавливаем search_path для использования схемы oozo-schema
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,
    max_overflow=20,
    echo=False,  # Установите True для отладки SQL запросов
    connect_args={
        "options": "-csearch_path=oozo-schema,public"
    }
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Путь к директории с миграциями
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


def get_migration_files():
    """
    Получает список файлов миграций в порядке применения
    """
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"Директория миграций не найдена: {MIGRATIONS_DIR}")
        return []
    
    migration_files = sorted([
        f for f in MIGRATIONS_DIR.glob("*.sql")
        if f.name.startswith("0") and f.name != "000_check_tables.sql"
    ])
    
    return migration_files


def apply_migration(migration_file: Path):
    """
    Применяет SQL миграцию из файла
    """
    try:
        logger.info(f"Применение миграции: {migration_file.name}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with engine.connect() as conn:
            # Выполняем миграцию в транзакции
            trans = conn.begin()
            try:
                conn.execute(text(sql_content))
                trans.commit()
                logger.info(f"Миграция {migration_file.name} успешно применена")
            except Exception as e:
                trans.rollback()
                logger.error(f"Ошибка при применении миграции {migration_file.name}: {e}")
                raise
                
    except Exception as e:
        logger.error(f"Ошибка при чтении/применении миграции {migration_file}: {e}")
        raise


def run_migrations():
    """
    Применяет все миграции из директории migrations
    """
    migration_files = get_migration_files()
    
    if not migration_files:
        logger.warning("Миграции не найдены, используем SQLAlchemy для создания таблиц")
        Base.metadata.create_all(bind=engine)
        return
    
    logger.info(f"Найдено миграций: {len(migration_files)}")
    
    for migration_file in migration_files:
        try:
            apply_migration(migration_file)
        except Exception as e:
            logger.error(f"Не удалось применить миграцию {migration_file.name}: {e}")
            raise


def init_db():
    """
    Инициализация базы данных - применение миграций или создание таблиц через SQLAlchemy
    """
    try:
        logger.info("Инициализация базы данных...")
        
        # Пытаемся применить миграции из SQL файлов
        migration_files = get_migration_files()
        if migration_files:
            logger.info("Найдены SQL миграции, применяем их...")
            run_migrations()
        else:
            logger.info("SQL миграции не найдены, используем SQLAlchemy для создания таблиц...")
            Base.metadata.create_all(bind=engine)
        
        logger.info("База данных успешно инициализирована")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для FastAPI - получение сессии БД
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с БД вне FastAPI
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при работе с БД: {e}")
        raise
    finally:
        db.close()

