# app/core/config.py
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ENV = os.getenv("APP_ENV", "dev")
env_file_path = f".env.{APP_ENV}"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file_path if os.path.exists(env_file_path) else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
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

    # 필수 JWT 설정에 합리적인 기본값 추가
    # 이 값들은 실제 운영 시 Terraform을 통해 주입된 값으로 덮어쓰여집니다.
    # 이 기본값은 Alembic 실행 등, 모든 환경 변수가 필요 없는 컨텍스트에서 오류를 방지합니다.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Firebase
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH: str
    FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64: str | None = None

    # AWS S3
    S3_BUCKET_NAME: str | None = None

    # gemini api
    GEMINI_MODEL_NAME: str = Field(default="models/gemini-2.5-flash-preview-05-20")

    # API Key 정책 설정
    API_KEY_PREFIX_LENGTH: int = 8
    API_KEY_SECRET_LENGTH: int = 32
    API_KEY_MAX_RETRIES: int = 5  # 키 생성 재시도 횟수


settings = Settings()
