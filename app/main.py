import asyncio

import uvicorn
from fastapi import FastAPI

from app.bot.bot_instance import bot
from app.bot.bot_launcher import dp
from app.bot.router import register_handlers
from app.db.database import engine, Base
from app.api.endpoints.lead import router

app = FastAPI()

app.include_router(router)

# Инициализация БД при запуске FastAPI
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    register_handlers(dp)  # Регистрируем все хендлеры бота
    asyncio.create_task(dp.start_polling(bot))  # Запускаем бота в фоне

@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)