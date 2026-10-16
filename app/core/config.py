from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    SECRET_KEY: str = "trendaura-super-secret-key-change-in-production-2026-unisex-fastapi"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_EMAIL: str = "admin@trendaura.pk"

    # Databases (Neon Async)
    DATABASE_URL: str = "sqlite+aiosqlite:///./trendaura.db"
    DATABASE_URL_DIRECT: Optional[str] = None

    # Custom Payment: Institutional Bank Transfer
    BANK_NAME: str = "Standard Chartered Bank"
    BANK_ACCOUNT_TITLE: str = "TrendAura Official Retail Ltd"
    BANK_ACCOUNT_NUMBER: str = "010293847501"
    BANK_IBAN: str = "PK36SCBL00000010293847501"

    # Business Rules
    REFUND_AUTO_APPROVE_LIMIT: float = 5000.0
    FRAUD_FLAG_THRESHOLD: int = 50

    # Cloudinary & AI (Phase 3)
    CLOUDINARY_URL: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None


settings = Settings()
