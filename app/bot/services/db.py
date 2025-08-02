import logging
from datetime import datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session, async_session_maker
from app.db.models.agent import Agent
from app.db.models.lead import Lead


logger = logging.getLogger(__name__)

'''Сохранение лида в БД'''
async def create_lead_in_db(session: AsyncSession, bitrix_id, title, budget = None, currency = None, lead_type = None) -> dict:
    # Проверка на существование
    result = await session.execute(select(Lead).where(Lead.bitrix_id == str(bitrix_id)))
    if result.scalar_one_or_none():
        return {"success": False} # Данный лид уже существует

    lead = Lead(
        bitrix_id=str(bitrix_id),
        title=title,
        budget=str(budget),
        currency=currency,
        lead_type=lead_type,
        created_at=datetime.now()
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)

    return {"success": True}


'''Маппинг Bitrix ID → Telegram ID'''
async def map_bitrix_to_telegram(users: list[dict], session: AsyncSession) -> list[dict]:
    if not users:
        return []

    bitrix_ids = [user["USER_ID"] for user in users if "USER_ID" in user]

    # Получаем агентов с нужными bitrix_user_id
    result = await session.execute(
        select(Agent).where(Agent.bitrix_user_id.in_(bitrix_ids))
    )
    agents = result.scalars().all()

    # Формируем список словарей
    mapped = [
        {"bitrix_id": agent.bitrix_user_id, "telegram_id": agent.telegram_id}
        for agent in agents
    ]
    return mapped


'''Получение агента по Telegram ID'''
async def get_agent_by_tg_id(telegram_id):
    async with async_session_maker() as session:
        agent_query = await session.execute(select(Agent).where(Agent.telegram_id == str(telegram_id)))
        agent = agent_query.scalar_one_or_none()
        return {"success": True, "value": agent}


'''Получение лида по Bitrix ID'''
async def get_lead_by_id(lead_id):
    async with async_session_maker() as session:
        lead_query = await session.execute(select(Lead).where(Lead.bitrix_id == str(lead_id)))
        lead = lead_query.scalar_one_or_none()
        return {"success": True, "value": lead}


'''Получение языка агента'''
async def get_lang_at_agent(telegram_id) -> dict | None:
    async with async_session_maker() as session:
        lang_query = await session.execute(select(Agent.language).where(Agent.telegram_id == str(telegram_id)))
        lang = lang_query.scalar_one_or_none()
        return {"success": True, "value": lang}


'''Проверка лида на занятость'''
async def checking_free_lead(lead_id) -> dict | None:
    print("lead_id", lead_id)
    async with async_session_maker() as session:
        lead_query = await session.execute(select(Lead).where(Lead.bitrix_id == str(lead_id)))
        lead = lead_query.scalar_one_or_none()
        print("lead", lead)
        if not lead or lead.assigned_id is not None:
            return {"success": False} # заявка уже взята другим
        return {"success": True, "value": lead} # заявка свободна


'''Проверка на существование агента'''
async def checking_is_agent(telegram_id) -> dict | None:
    async with async_session_maker() as session:
        agent_query = await session.execute(select(Agent).where(Agent.telegram_id == str(telegram_id)))
        agent = agent_query.scalar_one_or_none()
        if not agent:
            return {"success": False} # агент не найден
        return {"success": True, "value": agent} # агент существует


'''Проверка на занятость агента'''
async def checking_free_agent(agent_id) -> dict | None:
    async with async_session_maker() as session:
        free_agent_query = await session.execute(select(Lead).where(
            Lead.assigned_id == int(agent_id),
            Lead.comment == None,
            Lead.is_commented == False,
            Lead.stage_set == False)
        )
        free_agent = free_agent_query.scalars().first()
        if free_agent:
            return {"success": False} # агент занят
        return {"success": True} # агент свободен


'''Сохранение ответственного за лид в БД'''
async def assigning_agent_lead(lead, agent):
    async with async_session_maker() as session:
        lead.assigned_id = agent.id
        lead.taken_at = datetime.now()
        session.add(lead)
        await session.commit()


'''Проверка есть ли у лида комментарий'''
async def check_is_comment_by_lead(lead):
    async with async_session_maker() as session:
        lead_query = await session.execute(select(Lead).where(Lead.bitrix_id == lead.bitrix_id))
        lead = lead_query.scalar_one_or_none()
        # Если уже есть комментарий или стадия изменилась, ничего не делать
        if lead is None or lead.comment or lead.is_commented or lead.stage_set:
            return {"success": False} # комментарий есть
        return {"success": True}  # комментария нет


'''Обновить статус нажатия на кнопку Оставить комментарий'''
async def status_comment(lead_id):
    async with async_session_maker() as session:
        lead_query = await session.execute(select(Lead).where(Lead.bitrix_id == str(lead_id)))
        lead = lead_query.scalar_one_or_none()

        lead.is_commented = True
        session.add(lead)  # обязательно добавляем в сессию
        await session.commit()
        return {"success": True}


'''Сохранение комментария'''
async def save_comment(lead_id, comment):
    async with async_session_maker() as session:
        lead_query = await session.execute(select(Lead).where(Lead.bitrix_id == str(lead_id)))
        lead = lead_query.scalar_one_or_none()

        lead.comment = comment
        session.add(lead)  # обязательно добавляем в сессию
        await session.commit()


async def registration_user(telegram_id, bitrix_user_id, name, email, language):

    email = email.strip().lower()
    language = language.strip().lower()

    async with async_session_maker() as session:
        email = email.strip().lower()
        language = language.strip().lower()

        query = await session.execute(select(Agent).where(Agent.telegram_id == str(telegram_id)))
        existing_agent = query.scalar_one_or_none()

        if not existing_agent:
            # Создание нового агента
            new_agent = Agent(
                telegram_id=str(telegram_id),
                bitrix_user_id=str(bitrix_user_id),
                name=name,
                email=email,
                language=language
            )
            session.add(new_agent)
            await session.commit()
            return {"success": True}
        else:
            return {"success": False}



async def update_lang(telegram_id, lang):
    async with async_session_maker() as session:
        agent_query = await session.execute(select(Agent).where(Agent.telegram_id == str(telegram_id)))
        agent = agent_query.scalar_one_or_none()
        agent.language = lang
        session.add(agent)
        await session.commit()
