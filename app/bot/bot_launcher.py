from aiogram import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.bot.bot_instance import bot
from app.bot.router import register_handlers

dp = Dispatcher(bot, storage=MemoryStorage())
register_handlers(dp)

async def start_bot():
    await dp.start_polling(skip_updates=True)
