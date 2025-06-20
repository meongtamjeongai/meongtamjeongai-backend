# fastapi_backend/app/schemas/conversation.py
# Conversation 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.phishing_category import PhishingCategoryEnum
from app.schemas.base_schema import BaseModel
from app.schemas.persona import PersonaResponse  # 대화방 목록에 페르소나 정보 포함
from app.schemas.phishing import PhishingCaseResponse
from app.schemas.user import UserResponse


# 대화방 목록에 마지막 메시지 요약을 포함하기 위한 스키마 (선택적)
class ConversationLastMessageSummary(BaseModel):
    content: str
    sender_type: str  # SenderType Enum을 직접 사용하거나 문자열로
    created_at: datetime


class ConversationBase(BaseModel):
    title: Optional[str] = Field(
        None, max_length=255, description="대화방 제목 (선택 사항)"
    )


class ConversationCreate(
    BaseModel
):  # ConversationBase를 상속하지 않고 필요한 필드만 명시
    persona_id: int = Field(..., description="대화를 시작할 페르소나의 ID")
    title: Optional[str] = Field(
        None, max_length=255, description="대화방 제목 (미지정 시 자동 생성 가능)"
    )
    # user_id는 인증된 사용자로부터 자동으로 설정


class ConversationCreateWithCategory(ConversationCreate):
    """
    특정 피싱 카테고리를 지정하여 대화방을 생성하기 위한 요청 스키마입니다.
    ConversationCreate를 상속받아 persona_id와 title 필드를 재사용합니다.
    """

    category_code: PhishingCategoryEnum = Field(
        ..., description="적용할 피싱 시나리오의 유형(카테고리)"
    )


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    # persona_id: int # PersonaResponse에 포함되므로 중복일 수 있음
    persona: PersonaResponse  # 대화 상대 페르소나 정보 포함
    created_at: datetime
    last_message_at: datetime
    applied_phishing_case_id: Optional[int] = None
    # last_message_summary: Optional[ConversationLastMessageSummary] = None # 마지막 메시지 요약 (필요시)

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }


# 👇 관리자용 응답 스키마
class ConversationAdminResponse(ConversationResponse):
    """관리자용 대화방 응답 스키마. 사용자 정보를 포함합니다."""

    user: UserResponse
    applied_phishing_case: Optional[PhishingCaseResponse] = None


# 👇 관리자용 대화방 생성 요청 스키마
class ConversationCreateAdmin(BaseModel):
    """관리자가 대화방을 생성할 때 사용하는 스키마."""

    user_id: int = Field(..., description="대화방을 생성할 대상 사용자의 ID")
    persona_id: int = Field(..., description="대화할 페르소나의 ID")
    title: Optional[str] = Field(
        None, max_length=255, description="대화방 제목 (선택 사항)"
    )


# 관리자가 특정 카테고리를 지정하여 대화방을 생성하기 위한 스키마
class ConversationCreateAdminWithCategory(ConversationCreateAdmin):
    """
    관리자가 특정 피싱 카테고리를 지정하여 대화방을 생성할 때 사용하는 스키마.
    ConversationCreateAdmin을 상속받아 user_id, persona_id, title 필드를 재사용합니다.
    """

    category_code: PhishingCategoryEnum = Field(
        ..., description="적용할 피싱 시나리오의 유형(카테고리)"
    )
