from aiogram import Dispatcher

from app.bot.handlers import start, language, lead, registration


def register_handlers(dp: Dispatcher):
    start.register(dp)
    language.register(dp)
    lead.register(dp)
    registration.register(dp)