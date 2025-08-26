import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bot.bot_instance import bot
from app.bot.bot_launcher import dp
from app.bot.router import register_handlers
from app.db.database import engine, Base
from app.api.endpoints.lead import router
from app.logging_config import logger


# Инициализация FastAPI-приложения
app = FastAPI()

# Подключение CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение всех API роутов
app.include_router(router)


"""Действия при запуске приложения"""
@app.on_event("startup")
async def on_startup():
    logger.info("Инициализация приложения...")

    # Создание таблиц в БД, если их нет
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("База данных инициализирована")
    except Exception:
        logger.exception("Ошибка при инициализации базы данных")
        raise

    # Регистрация всех хэндлеров бота
    try:
        register_handlers(dp)
        logger.info("Хэндлеры Telegram-бота зарегистрированы")
    except Exception:
        logger.exception("Ошибка при регистрации хэндлеров бота")
        raise

    # Запуск бота в фоне
    asyncio.create_task(dp.start_polling(bot))
    logger.info("Telegram-бот запущен в режиме polling")


"""Действия при остановке приложения"""
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Остановка приложения...")

    # Закрываем сессию бота
    await bot.session.close()
    logger.info("Сессия Telegram-бота закрыта")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    logger.info("Приложение запущено!")