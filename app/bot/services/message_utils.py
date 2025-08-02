from app.bot.services.db import get_agent_by_tg_id
from app.shared.i18n import get_message


async def create_new_lead_message(telegram_id, lead):
    # Получение агента по telegram_id
    agent = await get_agent_by_tg_id(telegram_id=telegram_id)

    if not agent['success']:
        print(f"❌ Агент с telegram_id={telegram_id} не найден в БД")
        return {"success": False}

    lang = agent["value"].language
    try:
        title = lead["result"]["TITLE"]
        budget = lead["result"]["OPPORTUNITY"]
        currency = lead["result"]["CURRENCY_ID"]
        lead_type = lead["result"]["TYPE_ID"]
    except KeyError as k:
        title = lead["TITLE"]
        budget = lead["OPPORTUNITY"]
        currency = lead["CURRENCY_ID"]
        lead_type = lead["TYPE_ID"]


    text = get_message(
        lang=lang,
        key="new_lead",
        title=title,
        budget=budget,
        currency=currency if currency is not None else '',
        type=lead_type
    )

    return {"success": True, "value": text}

async def create_text_send_message(telegram_id, key_msg, **kwargs):
    # Получение агента по telegram_id
    agent = await get_agent_by_tg_id(telegram_id=telegram_id)

    if not agent:
        print(f"❌ Агент с telegram_id={telegram_id} не найден в БД")
        return {"success": False}

    lang = agent["value"].language

    text = get_message(
        lang=lang,
        key=key_msg,
        **kwargs
    )

    return {"success": True, "value": text}

async def create_contact_message(telegram_id, contact_data):
    # Получение агента по telegram_id
    agent = await get_agent_by_tg_id(telegram_id=telegram_id)

    if not agent:
        print(f"❌ Агент с telegram_id={telegram_id} не найден в БД")
        return {"success": False}

    lang = agent["value"].language
    contact_name = contact_data.get("NAME", None)
    contact_last_name = contact_data.get("LAST_NAME", None)
    contact_second_name = contact_data.get("SECOND_NAME", None)
    contact_phone = contact_data.get("PHONE", None)
    contact_email = contact_data.get("EMAIL", None)


    text = get_message(
        lang=lang,
        key="contact_info",
        contact_name=contact_name if contact_name is not None else '',
        contact_last_name=contact_last_name if contact_last_name is not None else '',
        contact_second_name=contact_second_name if contact_second_name is not None else '',
        contact_phone=contact_phone if contact_phone is not None else '',
        contact_email=contact_email if contact_email is not None else ''
    )

    return {"success": True, "value": text}

async def create_detail_lead_message(telegram_id, lead, contact_message):
    # Получение агента по telegram_id
    agent = await get_agent_by_tg_id(telegram_id=telegram_id)

    if not agent:
        print(f"❌ Агент с telegram_id={telegram_id} не найден в БД")
        return {"success": False}

    lang = agent["value"].language
    title = lead.get("TITLE", "Без названия")
    budget = lead.get("OPPORTUNITY", "Не указано")
    currency = lead.get("CURRENCY_ID", None)
    lead_type = lead.get("TYPE_ID", "Тип не указан")
    contact_id = lead.get("CONTACT_ID", "Контакт не указан")

    text = get_message(
        lang=lang,
        key='lead_detail',
        title=title,
        budget=budget,
        currency=currency if currency is not None else '',
        type=lead_type,
        contact=contact_message
    )

    return {"success": True, "value": text}