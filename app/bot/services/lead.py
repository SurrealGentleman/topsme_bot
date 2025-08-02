import asyncio
from datetime import datetime, timezone

from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.bot_instance import bot
from app.bot.keyboards.keyboards import get_take_keyboard
from app.bot.services.api import post_bitrix_request_aio
from app.bot.services.db import create_lead_in_db, map_bitrix_to_telegram, checking_free_lead, assigning_agent_lead, \
    checking_is_agent, checking_free_agent, check_is_comment_by_lead
from app.bot.services.message_utils import create_new_lead_message, create_text_send_message
from app.config.settings import get_settings


settings = get_settings()


'''Процесс: Получение инфы о лиде -> Сохранение инфы в бд -> Получение списка агентов -> Отправка заявки в тг'''
async def process_new_lead(lead_id: str, session: AsyncSession):

    # Получение детальной информации о лиде
    lead_data = await post_bitrix_request_aio(endpoint="crm.deal.get", json={"id": lead_id})
    lead_data_detail = lead_data.get("result", {})

    if lead_data_detail.get("CATEGORY_ID") == settings.BITRIX_FUNNEL_CATEGORY_ID_LEAD:

        # Сохраняем лид в бд
        await create_lead_in_db(
            session=session,
            bitrix_id=lead_data_detail["ID"],
            title=lead_data_detail.get("TITLE"),
            budget=lead_data_detail.get("OPPORTUNITY"),
            currency=lead_data_detail.get("CURRENCY_ID"),
            lead_type=lead_data_detail.get("TYPE_ID")
        )

        # Получаем список агентов из группы в Bitrix24
        response = await post_bitrix_request_aio(endpoint="sonet_group.user.get", json={"ID": settings.BITRIX_GROUP_ID})
        users_in_group = response.get("result", [])
        agents = await map_bitrix_to_telegram(users_in_group, session)

        # Отправляем им информацию через бота
        await asyncio.gather(*[
            send_lead_to_agent(agent["telegram_id"], lead_data)
            for agent in agents
        ], return_exceptions=True)


'''Назначение агента на заявку'''
async def take_lead_and_get_details(callback, state: FSMContext):
    lead_id = callback.data.split("_")[1]
    telegram_id = callback.from_user.id
    # lang = await get_lang_at_agent(telegram_id=telegram_id)

    free_lead = await checking_free_lead(lead_id=lead_id)

    if free_lead["success"]: # заявка свободна
        agent = await checking_is_agent(telegram_id=telegram_id)
        if agent["success"]: # агент существует
            free_agent = await checking_free_agent(agent_id=agent["value"].id)
            if free_agent["success"]: # агент свободен
                # Обновляем ответственного в базе
                await assigning_agent_lead(lead=free_lead["value"], agent=agent["value"])
                # Обновляем ответственного в Bitrix
                print("free_lead[value].bitrix_id", free_lead["value"].bitrix_id)
                print("agent[value].bitrix_user_id", agent["value"].bitrix_user_id)
                await post_bitrix_request_aio(endpoint="crm.deal.update.json", json={
                    "id": free_lead["value"].bitrix_id,
                    "fields":{"ASSIGNED_BY_ID": agent["value"].bitrix_user_id}
                })
                # Напоминание об оставлении комментария
                asyncio.create_task(schedule_comment_reminder(lead=free_lead["value"], agent=agent["value"], state=state))
                return {"success": True}
            else:
                return {"success": False, "message": "agent_busy"}
        else:
            pass # агент не найден
    else:
        return {"success": False, "message": "lead_busy"}


'''Отправка новых лидов агентам'''
async def send_lead_to_agent(telegram_id: int, lead: dict):
    try:
        # Создание сообщения
        text = await create_new_lead_message(telegram_id=telegram_id, lead=lead)
        if not text["success"]:
            return {"success": False}
        # Создание клавиатуры
        print("lead", lead)
        try:
            reply_markup = await get_take_keyboard(telegram_id=telegram_id, lead_id=lead["result"]["ID"])
        except KeyError as k:
            reply_markup = await get_take_keyboard(telegram_id=telegram_id, lead_id=lead["ID"])
        # Отправка сообщения
        await bot.send_message(chat_id=telegram_id,
                               text=text["value"],
                               reply_markup=reply_markup)
        return {"success": True}
    except Exception as e:
        import traceback
        print(f"Непредвиденная ошибка при отправке запроса агенту {telegram_id}: {e}")
        traceback.print_exc()
        return {"success": False}


'''def Фоновая задача с отложенной отправкой сообщения'''
async def schedule_comment_reminder(lead, agent, state: FSMContext):
    await asyncio.sleep(30)  # 10 минут
    print("GOOOOOOOOOOOOOOO")
    # Проверить есть ли комментарий
    is_not_comment = await check_is_comment_by_lead(lead=lead)
    if not is_not_comment["success"]:
        print("STOOOOOOOOOOOOOOOOP")
        return {"success": False}
    print("GOOOOOOOOOOOOOOO2")
    # Создание сообщения
    text = await create_text_send_message(telegram_id=agent.telegram_id, key_msg="notification_of_comment")
    if not text["success"]:
        return {"success": False}
    # Отправка сообщения
    try:
        sent_message: Message = await bot.send_message(
            chat_id=agent.telegram_id,
            text=text["value"]
        )
        # Сохранение message_id в FSMContext
        await state.update_data(notification_comment_message_id=sent_message.message_id)
        return {"success": True}
    except Exception as e:
        print(f"[ERROR] Не удалось отправить напоминание: {e}")
        return {"success": False}


'''Проверка на эффективность агента'''
# async def can_agent_take_lead(agent_user_id: str) -> tuple[bool, list[str]]:
#     """Проверяет, можно ли агенту брать лиды."""
#     reasons = []
#
#     # 1. Просроченные дела
#     overdue_tasks = await get_overdue_activities(agent_user_id)
#     if overdue_tasks:
#         reasons.append(f"🔴 Просроченные дела: {len(overdue_tasks)}")
#
#     # # 3. Нет следующего шага
#     # no_followup = await get_leads_without_followup(int(agent_user_id))
#     # if no_followup:
#     #     reasons.append(f"🟡 Не назначен следующий шаг: {len(no_followup)}")
#
#     return len(reasons) == 0, reasons


# async def get_overdue_activities(agent_id):
#     result = await post_bitrix_request_aio("crm.activity.list", {
#         "filter": {
#             "RESPONSIBLE_ID": agent_id,
#             "<DEADLINE": datetime.now().isoformat(),
#             "COMPLETED": "N"
#         }
#     })
#     return result.get("result", [])
#
# async def get_leads_without_followup(agent_id: int) -> list[dict]:
#     # Получаем все активные лиды агента
#     leads_response = await post_bitrix_request_aio("crm.deal.list", {
#         "filter": {
#             "ASSIGNED_BY_ID": agent_id,
#             "!STATUS_ID": ["WON", "LOSE", "APOLOGY"],  # исключаем завершённые
#         },
#         "select": ["ID", "TITLE"]
#     })
#
#     leads = leads_response.get("result", [])
#     leads_without_task = []
#
#     for lead in leads:
#         lead_id = lead["ID"]
#
#         # Получаем незавершённые дела по этому лиду
#         activities = await post_bitrix_request_aio("crm.activity.list", {
#             "filter": {
#                 "OWNER_TYPE_ID": 2,  # 2 = Deal
#                 "OWNER_ID": lead_id,
#                 "COMPLETED": "N"
#             },
#             "select": ["DEADLINE"]
#         })
#
#         has_future_task = False
#         for activity in activities.get("result", []):
#             deadline_str = activity.get("DEADLINE")
#             if not deadline_str:
#                 continue
#
#             try:
#                 deadline_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
#                 if deadline_dt > datetime.now(timezone.utc):
#                     has_future_task = True
#                     break
#             except Exception:
#                 continue
#
#         if not has_future_task:
#             leads_without_task.append(lead)
#
#     return leads_without_task


async def get_open_tasks(agent_id: int) -> list[dict]:
    """
    Возвращает список всех незавершённых задач (дел) агента.
    """
    response = await post_bitrix_request_aio("crm.activity.list", {
        "filter": {
            "RESPONSIBLE_ID": agent_id,
            "COMPLETED": "N"
        },
        "select": ["ID", "OWNER_ID", "OWNER_TYPE_ID", "SUBJECT", "OWNER_TYPE"]
    })
    return response.get("result", [])

def format_task_links(tasks: list[dict]) -> str:
    """
    Формирует ссылки на открытые задачи с кратким описанием.
    """
    lines = []
    for task in tasks:
        owner_type = task.get("OWNER_TYPE", "deal").lower()  # обычно 'lead' или 'deal'
        owner_id = task["OWNER_ID"]
        subject = task.get("SUBJECT", "Без названия")
        url = f"{settings.BITRIX_URL}{owner_type}/details/{owner_id}/"

        lines.append(f"🔹 [{subject}]({url})")

    return "\n".join(lines)

