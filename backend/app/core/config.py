from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NYAYA SETU"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://nyaya_user:nyaya_password@localhost:5432/nyaya_setu"

    # JWT
    SECRET_KEY: str = "change-this-secret-key-in-production-minimum-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # Background alert scanner (timeline / reminder / escalation / overlap alerts)
    ALERT_SCAN_ENABLED: bool = True
    ALERT_SCAN_INTERVAL_MINUTES: int = 15

    # Optional AI
    AI_SERVICE_URL: str = ""
    AI_SERVICE_ENABLED: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
