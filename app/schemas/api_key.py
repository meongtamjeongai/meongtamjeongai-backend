# app/schemas/api_key.py
import enum
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .base_schema import BaseModel


class ApiKeyScope(str, enum.Enum):
    """API 키에 부여할 수 있는 권한 범위(스코프) 정의"""
    PHISHING_CREATE = "phishing:create"
    PHISHING_READ = "phishing:read"
    # 필요에 따라 다른 스코프 추가 가능 (e.g., "users:read", "personas:update")


class ApiKeyCreate(BaseModel):
    """API 키 생성 요청 시 사용될 스키마"""
    description: str = Field(..., description="API 키의 용도에 대한 설명")
    scopes: List[ApiKeyScope] = Field(..., description="이 키에 부여할 권한 목록")
    expires_in_days: Optional[int] = Field(
        None, ge=1, description="키 만료까지의 일수 (미지정 시 무제한)"
    )


class ApiKeyResponse(BaseModel):
    """API 키 목록 조회 시 반환될 스키마 (민감 정보 제외)"""
    id: int
    key_prefix: str
    description: Optional[str]
    scopes: List[str]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NewApiKeyResponse(ApiKeyResponse):
    """
    API 키 생성 직후, 원본 키를 포함하여 딱 한 번만 반환되는 스키마
    """
    api_key: str = Field(..., description="생성된 API 키 원본. 이 값을 복사하여 사용하세요.")
