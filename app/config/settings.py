from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # База данных
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # Интеграции
    BITRIX_URL: str
    BITRIX_WEBHOOK: str
    BITRIX_GROUP_ID: int
    BITRIX_BOT_BUFFER_ID: int
    BITRIX_FUNNEL_CATEGORY_ID_LEAD: int
    BITRIX_FUNNEL_NEW_BUILDING_ID: int
    BITRIX_FUNNEL_VILLA_ID: int
    BOT_TOKEN: str

    SQL_ECHO: bool


    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
