from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext

from app.bot.keyboards.keyboards import get_language_keyboard
from app.bot.services.db import get_agent_by_tg_id, update_lang
from app.bot.states import Registration
from app.shared.i18n import get_message


async def language_handler(message: types.Message):
    await message.answer(get_message(lang='start', key='SELECT_LANGUAGE'), reply_markup=await get_language_keyboard())

async def language_selected(callback: types.CallbackQuery, state: FSMContext):
    agent = await get_agent_by_tg_id(callback.message.chat.id)
    lang_code = callback.data.split("_")[1]
    if not agent["value"]:
        await state.update_data(language=lang_code)
        await callback.message.edit_text(get_message(lang=lang_code, key='success_lang_select'))
        await callback.message.answer(get_message(lang=lang_code, key='enter_email'))
        await Registration.waiting_for_email.set()
    else:
        await update_lang(callback.message.chat.id, lang_code)
        await callback.message.edit_text(get_message(lang=lang_code, key='success_lang_select'))


def register(dp: Dispatcher):
    dp.register_message_handler(language_handler, commands=['language'])
    dp.register_callback_query_handler(language_selected, lambda c: c.data.startswith("lang_"))
