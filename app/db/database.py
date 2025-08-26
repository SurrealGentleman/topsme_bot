from typing import Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config.settings import get_settings
from app.logging_config import logger


# Загружается конфигурация приложения
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
SQL_ECHO = settings.SQL_ECHO

# Асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO, future=True)
logger.info(f"Создан async engine для базы данных: {DATABASE_URL}")

# Фабрика для создания сессий
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс для моделей ORM
Base = declarative_base()


"""
Асинхронный генератор сессий для работы с БД.
Используется в зависимостях FastAPI.
"""
async def get_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    try:
        logger.debug("Создание новой сессии базы данных")
        async with async_session_maker() as session:
            yield session
    except Exception:
        logger.exception("Ошибка при работе с сессией базы данных")
        raise
    finally:
        logger.debug("Закрытие сессии базы данных")

