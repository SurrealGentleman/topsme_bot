from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.services.api import post_bitrix_request_aio
from app.bot.services.db import get_lang_at_agent
from app.shared.i18n import get_message


async def get_language_keyboard() -> InlineKeyboardMarkup:
    lang_dict = get_message(lang='start', key='LANGUAGES')
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=callback_data)] for callback_data, label in lang_dict.items()
        ]
    )

async def get_take_keyboard(telegram_id, lead_id) -> InlineKeyboardMarkup:
    lang = await get_lang_at_agent(telegram_id)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_message(lang=lang["value"], key='take_button'),
                callback_data=f"take_{lead_id}"
            )]
        ]
    )

async def get_comment_keyboard(telegram_id, lead_id) -> InlineKeyboardMarkup:
    lang = await get_lang_at_agent(telegram_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=get_message(lang=lang["value"], key='leave_comment_button'),
                callback_data=f"leave_comment:{lead_id}"
            )]
        ]
    )

async def get_stage_keyboard(stages: list[dict], lead_id: int, current_stage_id: str, category_id) -> InlineKeyboardMarkup:
    # kb = InlineKeyboardMarkup(row_width=2)
    # for stage in stages:
    #     kb.add(
    #         InlineKeyboardButton(
    #             text=f"✅ {stage['name']}" if stage["stage_id"] == current_stage_id else stage['name'],
    #             callback_data=f"set_stage:{lead_id}:{stage['stage_id']}"
    #         )
    #     )
    # # return kb
    print("stages_kb", stages)
    print("lead_id_kb", lead_id)
    print("current_stage_id_kb", current_stage_id)
    print("category_id", category_id)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ {stage['name']}" if stage["stage_id"] == current_stage_id else stage['name'],
                                  callback_data=f"set_stage|{lead_id}|{stage['stage_id']}|{category_id}")]
            for stage in stages
        ]
    )
