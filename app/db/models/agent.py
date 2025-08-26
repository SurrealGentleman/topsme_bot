from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    bitrix_user_id = Column(Integer, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    is_employee = Column(Boolean, default=False)
    is_candidate = Column(Boolean, default=False)
    manual_override = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.now)
    language = Column(String)

    leads = relationship("Lead", back_populates="agent")