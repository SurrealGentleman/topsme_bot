from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True, index=True)
    bitrix_id = Column(String, unique=True, index=True)
    title = Column(String)
    budget = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    lead_type = Column(String, nullable=True)
    assigned_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    taken_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    comment = Column(String, nullable=True)  # 🆕 комментарий от агента
    is_commented = Column(Boolean, default=False)  # 🆕 флаг: оставлен ли комментарий
    stage_set = Column(Boolean, default=False)  # 🆕 флаг: стадия лида обновлена в CRM)

    agent = relationship("Agent", back_populates="leads")