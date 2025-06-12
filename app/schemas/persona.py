# fastapi_backend/app/schemas/persona.py
# Persona 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base_schema import BaseModel

# from app.schemas.user import UserResponse # 순환 참조 주의, 필요시 UserResponse의 일부만 포함하는 간략한 스키마 사용


# 페르소나 생성/수정 시 작성자 정보를 위한 간략한 스키마 (선택적)
class PersonaCreatorInfo(BaseModel):
    id: int
    username: Optional[str] = None
    email: Optional[str] = None  # EmailStr 사용 가능


class PersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="페르소나의 이름")
    description: Optional[str] = Field(None, description="페르소나에 대한 설명")
    profile_image_key: Optional[str] = Field(
        None, description="S3에 저장된 프로필 이미지의 Object Key"
    )
    system_prompt: str = Field(
        ..., description="Gemini API에 전달될 페르소나의 기본 지침"
    )
    is_public: bool = True


class PersonaCreate(PersonaBase):
    # created_by_user_id는 인증된 사용자로부터 자동으로 설정되므로 요청 본문에는 불필요
    pass


class PersonaUpdate(
    BaseModel
):  # 전체 업데이트가 아닌 부분 업데이트를 위해 필드들을 Optional로
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    profile_image_key: Optional[str] = None
    system_prompt: Optional[str] = None
    is_public: Optional[bool] = None


class PersonaResponse(PersonaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[int] = None  # 생성자 ID
    # creator: Optional[PersonaCreatorInfo] = None # 생성자 상세 정보 (필요시 주석 해제 및 PersonaCreatorInfo 사용)

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }
    # Pydantic V1
    # class Config:
    #     orm_mode = True
