from typing import Optional
from pydantic import BaseModel


class AgentRegisterRequest(BaseModel):
    telegram_id: str
    bitrix_user_id: str
    name: str
    email: str
    language: str

class CreateLeadRequest(BaseModel):
    bitrix_id: str
    title: str
    budget: Optional[str] = None
    currency: Optional[str] = None
    lead_type: Optional[str] = None

class TakeLeadRequest(BaseModel):
    lead_id: int
    telegram_id: str

class RequestCommentInput(BaseModel):
    lead_id: int

class CommentPayload(BaseModel):
    lead_id: int
    comment: str