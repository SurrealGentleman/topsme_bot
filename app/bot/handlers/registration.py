import logging
import traceback

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_instance import bot
from app.bot.services.api import post_bitrix_request_aio, settings
from app.bot.services.db import registration_user
from app.bot.states import Registration
from app.db.database import get_session
from app.db.models.agent import Agent
from app.shared.i18n import get_message

logger = logging.getLogger(__name__)

async def process_email(message: Message, state: FSMContext):
    email = message.text.strip().lower()
    name = message.from_user.full_name
    data = await state.get_data()
    lang = data.get("language")
    telegram_id = str(message.from_user.id)

    # Поиск пользователя
    bitrix_response = await post_bitrix_request_aio(endpoint="user.search", json={
        "FILTER": {
            "EMAIL": email
        }
    })

    user = bitrix_response.get("result", [])

    if user:
        bitrix_id = user[0]["ID"]
        # Добавление в БД
        result = await registration_user(telegram_id=telegram_id, bitrix_user_id=bitrix_id, name=name, email=email, language=lang)
        if not result["success"]:
            await bot.send_message(
                chat_id=message.chat.id,
                text=get_message(lang=lang, key='registration_already')
            )
            return

        # Добавление пользователя в группу в Bitrix
        await post_bitrix_request_aio(endpoint="sonet_group.user.add.json", json={
                "GROUP_ID": settings.BITRIX_GROUP_ID,
                "USER_ID": bitrix_id,
                "ROLE": "E"  # E = пользователь, A = админ, K = владелец
            })

        # Отправка сообщения об успешной регистрации
        await bot.send_message(
            chat_id=message.chat.id,
            text=get_message(lang=lang, key='registration_completed')
        )
        await state.finish()
    else:
        # Отправка сообщения об отклоненной регистрации
        await bot.send_message(
            chat_id=message.chat.id,
            text=get_message(lang=lang, key='email_not_found')
        )


def register(dp: Dispatcher):
    dp.register_message_handler(process_email, state=Registration.waiting_for_email)
