from aiogram import types, Dispatcher

from app.bot.services.db import get_agent_by_tg_id
from app.shared.i18n import get_message
from app.bot.keyboards.keyboards import get_language_keyboard


async def start_handler(message: types.Message):
    agent = await get_agent_by_tg_id(message.chat.id)
    if not agent["value"]:
        await message.answer(get_message(lang='start', key='SELECT_LANGUAGE'), reply_markup=await get_language_keyboard())
    else:
        await message.answer(get_message(lang=agent.language, key='registration_already'))

def register(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'])
