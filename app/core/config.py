# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ENV = os.getenv("APP_ENV", "dev")
env_file_path = f".env.{APP_ENV}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path if os.path.exists(env_file_path) else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application Settings
    APP_ENV: str = "dev"
    PROJECT_NAME: str = "멍탐정 API"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Firebase
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH: str
    FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64: str | None = None


settings = Settings()
