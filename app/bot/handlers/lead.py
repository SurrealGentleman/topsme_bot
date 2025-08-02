from dataclasses import fields

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from unicodedata import category

from app.bot.bot_instance import bot
from app.bot.keyboards.keyboards import get_comment_keyboard, get_take_keyboard, get_stage_keyboard
from app.bot.services.api import post_bitrix_request_aio, settings
from app.bot.services.db import status_comment, save_comment, get_lang_at_agent, get_agent_by_tg_id
from app.bot.services.lead import take_lead_and_get_details, get_open_tasks, format_task_links, send_lead_to_agent
from app.bot.services.message_utils import create_contact_message, \
    create_detail_lead_message, create_text_send_message, create_new_lead_message
from app.bot.states import Registration
from app.shared.i18n import get_message, localize_stage_names

'''Нажатие на кнопку Взять'''
async def take_lead_callback(callback: types.CallbackQuery, state: FSMContext):
    print("callback", callback)
    lead_id = callback.data.split("_")[1]
    telegram_id = callback.from_user.id
    # original_text_message = callback.message.text
    check_agent = await get_agent_by_tg_id(telegram_id)
    # Показываем, что мешает
    tasks = await get_open_tasks(check_agent["value"].bitrix_user_id)
    if len(tasks) == 0:
        result = await take_lead_and_get_details(callback, state=state)
        # Получить данные о заявке
        lead = await post_bitrix_request_aio(endpoint="crm.deal.get", json={"id": lead_id})

        if result["success"]:
            print("lead____", lead)
            # Получить данные о контакте
            contact = await post_bitrix_request_aio(endpoint="crm.contact.get", json={"id": lead["result"]["CONTACT_ID"]})
            print("contact", contact)
            # Создать сообщение о контакте
            contact_message = await create_contact_message(telegram_id=telegram_id, contact_data=contact["result"])
            print("contact_message", contact_message)
            # Создать сообщение с детальной информацией о сделке
            text_lead_message = await create_detail_lead_message(telegram_id=telegram_id, lead=lead["result"], contact_message=contact_message["value"])
            print("text_lead_message", text_lead_message)
            # Создать клавиатуру
            reply_markup = await get_comment_keyboard(telegram_id=telegram_id, lead_id=lead_id)
            # Обновить сообщение с заявкой
            msg_lead = await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=text_lead_message["value"],
                reply_markup=reply_markup
            )
            await state.update_data(
                original_lead_message_id=msg_lead.message_id,
                original_lead_text=msg_lead.text
            )
        elif not result["success"] and result["message"] == "lead_busy":
            # Создать сообщение о том что заявка уже занята
            text_lead_message = await create_text_send_message(telegram_id=telegram_id, key_msg="lead_taken_fail")
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=text_lead_message["value"],
                reply_markup=None
            )
        elif not result["success"] and result["message"] == "agent_busy":
            text = await create_new_lead_message(telegram_id=telegram_id, lead=lead)
            # Создать сообщение о том что агент занят
            text_lead_message = await create_text_send_message(telegram_id=telegram_id, key_msg="agent_taken_fail", original_text_message=text["value"])
            reply_markup = await get_take_keyboard(telegram_id=telegram_id, lead_id=lead_id)
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=text_lead_message["value"],
                reply_markup=reply_markup
            )
    else:
        message = (
            "❗ Вы не можете брать новые заявки.\n"
            "Закройте следующие задачи:\n\n"
            f"{format_task_links(tasks)}\n\n"
            "Как только вы выполните их, вернитесь в бот и попробуйте снова."
        )
        await bot.send_message(telegram_id, message)

'''Нажатие на кнопку Оставить комментарий по заявке'''
async def handle_comment_button(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split(":")[1])

    await status_comment(lead_id)
    await state.set_state(Registration.waiting_for_comment)
    await state.update_data(lead_id=lead_id, comment_message_id=callback.message.message_id)
    # Удаляем inline-кнопки
    await callback.message.edit_reply_markup(reply_markup=None)
    # Отправляем сообщение "Жду комментарий"
    text = await create_text_send_message(telegram_id=callback.message.chat.id, key_msg="wait_comment")
    wait_msg = await callback.message.answer(text["value"])
    await state.update_data(waiting_comment_message_id=wait_msg.message_id)


'''Ожидание сообщения с комментарием'''
async def receive_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lead_id = data.get("lead_id")
    comment_text = message.text
    telegram_id = message.chat.id

    # Сохранение комментария в БД
    await save_comment(lead_id=lead_id, comment=comment_text)

    # Отправка в Bitrix24 (замени на свою реализацию)
    await post_bitrix_request_aio(endpoint="crm.deal.update", json={
        "id": lead_id,
        "fields": {
            "COMMENTS": comment_text
        }
    })

    original_lead_text = data.get("original_lead_text")
    original_lead_message_id = data.get("original_lead_message_id")
    # original_message_id = data.get("comment_message_id")
    notification_comment_message_id = data.get("notification_comment_message_id")
    waiting_comment_message_id = data.get("waiting_comment_message_id")

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        print(f"Ошибка при удалении комментария пользователя: {e}")

    # Удаляем сообщение бота "Жду комментарий"
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_comment_message_id)
    except Exception as e:
        print(f"Ошибка при удалении 'Жду комментарий': {e}")

    # Удаляем напоминание, если оно было
    if notification_comment_message_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=notification_comment_message_id)
        except Exception as e:
            print(f"Ошибка при удалении напоминания: {e}")

    # Обновить стадию сделки
    await post_bitrix_request_aio(endpoint='crm.deal.update', json={
        "id": lead_id,
        "fields": {
            "STAGE_ID": "PREPARATION"
        }
    })


    # Обновляем оригинальное сообщение с заявкой
    try:
        updated_text = await create_text_send_message(telegram_id=telegram_id, key_msg="plus_comment",
                                                     original_lead_text=original_lead_text, comment_text=comment_text)
        print(updated_text)
        # Получаем стадии
        stages = await post_bitrix_request_aio(endpoint="crm.status.list", json={
            "order": { "SORT": "ASC" },
            "filter": {
                "ENTITY_ID": "DEAL_STAGE",
                "CATEGORY_ID": settings.BITRIX_FUNNEL_CATEGORY_ID_LEAD
            }
        })
        print(stages)

        lang = await get_lang_at_agent(telegram_id)
        print(lang)
        stages_proc = [{"stage_id": s["STATUS_ID"], "name": s["NAME"]} for s in stages["result"]]
        print(stages_proc)
        localized_stages = localize_stage_names(stages_proc[1:], lang["value"])
        print(localized_stages)
        current_stage_id = await post_bitrix_request_aio(endpoint='crm.deal.get', json={"id": lead_id})
        print(current_stage_id["result"]["STAGE_ID"])
        keyboard = await get_stage_keyboard(localized_stages, lead_id, current_stage_id["result"]["STAGE_ID"], category_id=settings.BITRIX_FUNNEL_CATEGORY_ID_LEAD)
        print(keyboard)




        msg_lead = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=original_lead_message_id,
            text=updated_text["value"],
            reply_markup=keyboard
        )

        # await state.update_data(
        #     original_lead_message_id=msg_lead.message_id,
        #     original_lead_text=msg_lead.text
        # )

    except Exception as e:
        print(f"Ошибка при обновлении сообщения с заявкой: {e}")

    await state.finish()


'''Нажатие на кнопку стадии'''
async def handle_stage_change(callback_query: types.CallbackQuery, state: FSMContext):
    print("STAGEEEEEEEEEEEEEE")
    await state.update_data(
        original_lead_message_id=callback_query.message.message_id,
        original_lead_text=callback_query.message.text
    )
    data = await state.get_data()
    print("data", data)
    user_id = callback_query.from_user.id
    callback_data = callback_query.data.split("|")
    lead_id = callback_data[1]
    stage_id = callback_data[2]
    category_id = callback_data[3]
    print("lead_id", lead_id)
    print("stage_id", stage_id)
    original_lead_text = data.get("original_lead_text")
    original_lead_message_id = data.get("original_lead_message_id")
    print("original_lead_message_id", original_lead_message_id)


    # Получаем сделку (предположим, ты знаешь, какую сделку редактирует пользователь)
    if not lead_id:
        print("Сделка не найдена")
        return

    # Обновляем стадию в CRM
    await post_bitrix_request_aio("crm.deal.update", json={
        "id": lead_id,
        "fields": {
            "STAGE_ID": stage_id,
            "CATEGORY_ID": category_id
        }
    })

    # Получаем список стадий
    if str(category_id) == settings.BITRIX_FUNNEL_CATEGORY_ID_LEAD:
        statuses = await post_bitrix_request_aio(endpoint="crm.status.list", json={
            "order": {"SORT": "ASC"},
            "filter": {
                "ENTITY_ID": "DEAL_STAGE",
                "CATEGORY_ID": category_id
            }
        })
    else:
        statuses = await post_bitrix_request_aio(endpoint="crm.status.list", json={
            "order": {"SORT": "ASC"},
            "filter": {
                "CATEGORY_ID": category_id
            }
        })

    if str(category_id) == settings.BITRIX_FUNNEL_VILLA_ID:
        stages = [status for status in statuses.get('result', [])
                             if status.get('STATUS_ID', '').startswith('C3:')]
    else:
        stages = statuses.get('result', [])

    print(stages)
    lang = await get_lang_at_agent(user_id)
    print("lang", lang)
    stages_proc = [{"stage_id": s["STATUS_ID"], "name": s["NAME"]} for s in stages]
    localized_stages = localize_stage_names(stages_proc[1:], lang["value"])
    # localized = localize_stage_names(stages, lang["value"])
    print("localized_stages", localized_stages)
    current_stage_id = await post_bitrix_request_aio(endpoint='crm.deal.get', json={"id": lead_id})
    print("current_stage_id", current_stage_id)


    print("stage_id", stage_id)
    # Проверяем, выбрана ли стадия WON (успешная сделка)
    if stage_id == "WON":
        # Предложить выбрать воронку для конвертации
        # await callback_query.message.answer("Выберите, в какую воронку конвертировать:")
        # await callback_query.message.answer(
        #     "1. Воронка Продажа новостроек\n2. Воронка Продажа виллы",
        #     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        #         [InlineKeyboardButton(text="Воронка Продажа новостроек", callback_data=f"convert:new_building:{lead_id}")],
        #         [InlineKeyboardButton(text="Воронка Продажа виллы", callback_data=f"convert:villa:{lead_id}")]
        #     ])
        # )
        new_text = get_message(lang=lang["value"], key="choice_funnel", original_lead_text=original_lead_text)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(get_message(lang=lang["value"], key="funnel_new_building"), callback_data=f"convert:new_building:{lead_id}")],
            [InlineKeyboardButton(get_message(lang=lang["value"], key="funnel_villa"), callback_data=f"convert:villa:{lead_id}")],
            [InlineKeyboardButton(get_message(lang=lang["value"], key="funnel_both"), callback_data=f"convert:both:{lead_id}")]
        ])
        await callback_query.message.edit_text(new_text, reply_markup=keyboard)
    elif stage_id in {"C1:WON", "C3:WON"}:
        new_text = get_message(lang=lang["value"], key="final_stage")
        await callback_query.message.edit_text(new_text)
    elif stage_id in {"LOSE", "APOLOGY", "UC_UL8WTL", "C1:LOSE", "C1:UC_GXE9DA", "C3:LOSE"}:  # сюда можно добавить свои "провальные"
        # Неуспешная стадия — просто обновим сообщение
        print("localized_stages", localized_stages)
        stage_name = next((s["name"] for s in localized_stages if s["stage_id"] == stage_id), stage_id)
        new_text = get_message(lang=lang["value"], key="lose_stage", original_lead_text=original_lead_text, stage_name=stage_name)
        await callback_query.message.edit_text(new_text)
    else:
        # Обновлённая клавиатура
        keyboard = await get_stage_keyboard(localized_stages, lead_id, current_stage_id["result"]["STAGE_ID"], category_id)
        print("keyboard", keyboard)
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)

    await callback_query.answer(get_message(lang=lang["value"], key="stage_update"))

'''Конвертация сделки'''
async def handle_conversion(callback_query: types.CallbackQuery):
    _, funnel_type, lead_id_str = callback_query.data.split(":")
    lead_id = int(lead_id_str)
    print(funnel_type)
    user_id = callback_query.from_user.id

    lang = await get_lang_at_agent(user_id)
    lead = await post_bitrix_request_aio(endpoint="crm.deal.get", json={"id": lead_id})
    lead_data_add = lead["result"]
    async def create_lead_and_send_ui(category_id: int, funnel_name: str):
        exclude_keys = [
            "ID", "CATEGORY_ID", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY",
            "CLOSED", "IS_RECURRING", "IS_WORK", "RECURRING_ID",
            "CONTACT_IDS", "COMPANY_ID", "ACTIVITY_ID", "ORIGIN_ID", "ORIGINATOR_ID"
        ]
        # Очищаем исходный словарь от лишних полей
        new_deal_data = {k: v for k, v in lead_data_add.items() if k not in exclude_keys}

        # Обновляем CATEGORY_ID на нужную воронку
        new_deal_data["CATEGORY_ID"] = category_id

        # Отправляем запрос на создание сделки
        response = await post_bitrix_request_aio(endpoint="crm.deal.add", json={"fields": new_deal_data})
        new_lead_id = response["result"]


        # Получение стадий новой воронки
        statuses = await post_bitrix_request_aio(endpoint="crm.status.list", json={
            "order": {"SORT": "ASC"},
            "filter": {
                "CATEGORY_ID": category_id
            }
        })

        if str(category_id) == settings.BITRIX_FUNNEL_VILLA_ID:
            stages = [status for status in statuses.get('result', [])
                      if status.get('STATUS_ID', '').startswith('C3:')]
        else:
            stages = statuses.get('result', [])




        stages_proc = [{"stage_id": s["STATUS_ID"], "name": s["NAME"]} for s in stages]
        print("TTTTTTTTT2", stages_proc)
        current_stage_id = await post_bitrix_request_aio(endpoint='crm.deal.get', json={"id": new_lead_id})
        print("TTTTTTTTT3", current_stage_id)
        localized_stages = localize_stage_names(stages_proc, lang["value"])
        print("TTTTTTTTT4", localized_stages)
        # keyboard = build_stage_keyboard(localized_stages, current_stage_id=None, deal_id=new_deal_id)
        keyboard = await get_stage_keyboard(localized_stages, new_lead_id, current_stage_id["result"]["STAGE_ID"], category_id)
        print("TTTTTTTTT5", keyboard)


        contact = await post_bitrix_request_aio(endpoint="crm.contact.get", json={"id": lead["result"]["CONTACT_ID"]})
        contact_message = await create_contact_message(telegram_id=callback_query.message.chat.id,
                                                       contact_data=contact["result"])
        text_lead_message = await create_detail_lead_message(telegram_id=callback_query.message.chat.id,
                                                             lead=lead["result"],
                                                             contact_message=contact_message["value"])
        # Отправка нового сообщения
        await callback_query.message.bot.send_message(
            chat_id=callback_query.from_user.id,
            text=get_message(lang=lang["value"], key="new_lead_new_funnel", text_lead_message=text_lead_message["value"], funnel_name=funnel_name),
            reply_markup=keyboard,
        )

    if funnel_type == "new_building":
        await create_lead_and_send_ui(settings.BITRIX_FUNNEL_NEW_BUILDING_ID, get_message(lang=lang['value'], key="funnel_new_building"))
        await callback_query.message.edit_text(get_message(lang=lang["value"], key="convert_lead_info_funnel_new_building"))

    elif funnel_type == "villa":
        await create_lead_and_send_ui(settings.BITRIX_FUNNEL_VILLA_ID, get_message(lang=lang['value'], key="funnel_villa"))
        await callback_query.message.edit_text(get_message(lang=lang["value"], key="convert_lead_info_funnel_villa"))

    elif funnel_type == "both":
        await create_lead_and_send_ui(settings.BITRIX_FUNNEL_NEW_BUILDING_ID, get_message(lang=lang['value'], key="funnel_new_building"))
        await create_lead_and_send_ui(settings.BITRIX_FUNNEL_VILLA_ID, get_message(lang=lang['value'], key="funnel_villa"))
        await callback_query.message.edit_text(get_message(lang=lang["value"], key="convert_lead_info_funnel_both"))

    await callback_query.answer()


async def handle_free_leads_command(message: types.Message):
    user_id = message.from_user.id

    # Проверка: является ли пользователь агентом
    is_agent = await get_agent_by_tg_id(user_id)
    if not is_agent["value"]:
        await message.answer("⛔ У вас нет прав для получения заявок.")
        return

    # Получаем список свободных лидов
    response = await post_bitrix_request_aio("crm.deal.list", {
            "filter": {
                "CATEGORY_ID": settings.BITRIX_FUNNEL_CATEGORY_ID_LEAD,
                "!STAGE_ID": ["WON", "LOSE"],  # исключаем завершённые
                "ASSIGNED_BY_ID": settings.BITRIX_BOT_BUFFER_ID  # бот — временно ответственный
            },
            "select": ["ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID", "TYPE_ID"]
        })
    free_leads = response.get("result", [])

    if not free_leads:
        await message.answer(get_message(lang=is_agent["value"].language, key="none_free_leads"))
        return

    for lead in free_leads:
        await send_lead_to_agent(user_id, lead)


def register(dp: Dispatcher):
    dp.register_callback_query_handler(take_lead_callback, lambda c: c.data.startswith("take_"))
    dp.register_callback_query_handler(handle_comment_button, lambda c: c.data.startswith("leave_comment:"))
    dp.register_message_handler(receive_comment, state=Registration.waiting_for_comment)
    dp.register_callback_query_handler(handle_stage_change, lambda c: c.data.startswith("set_stage|"))
    dp.register_callback_query_handler(handle_conversion, lambda c: c.data.startswith("convert:"))
    dp.register_message_handler(handle_free_leads_command, Command("free_leads"))


#set_stage:{lead_id}:{stage['id']}