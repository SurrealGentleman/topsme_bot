from fastapi import BackgroundTasks, Depends, Request, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.services.lead import process_new_lead
from app.db.database import get_session


router = APIRouter()

'''endpoint Обработка новых лидов'''
@router.post("/bitrix/webhook")
async def handle_bitrix_webhook(request: Request, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    # Получаем данные
    data = await request.form()
    lead_id = data.get("data[FIELDS][ID]")
    print("data", data)
    print("lead_id", lead_id)

    if lead_id:
        # Запускаем задачу в фоне для отправки лида
        background_tasks.add_task(process_new_lead, lead_id, session)
        return {"status": "ok"}

    return {"status": "error", "message": f"Нет лида с id={lead_id}"}
