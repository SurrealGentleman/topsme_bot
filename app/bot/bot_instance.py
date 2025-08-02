from aiogram import Bot
from app.config.settings import get_settings

settings = get_settings()
bot = Bot(token=settings.BOT_TOKEN)