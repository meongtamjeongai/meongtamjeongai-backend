# fastapi_backend/app/schemas/social_account.py
# SocialAccount 모델 관련 Pydantic 스키마

from datetime import datetime

from app.models.social_account import SocialProvider  # Enum 임포트
from app.schemas.base_schema import BaseModel


class SocialAccountBase(BaseModel):
    provider: SocialProvider
    provider_user_id: str


class SocialAccountCreate(SocialAccountBase):
    # user_id는 서비스 로직에서 채워지므로 요청 본문에는 불필요
    pass


class SocialAccountResponse(SocialAccountBase):
    id: int
    user_id: int
    created_at: datetime

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }
    # Pydantic V1
    # class Config:
    #     orm_mode = True
