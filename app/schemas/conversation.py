# fastapi_backend/app/schemas/conversation.py
# Conversation 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base_schema import BaseModel
from app.schemas.persona import PersonaResponse  # 대화방 목록에 페르소나 정보 포함

# from app.schemas.message import MessageResponse # 마지막 메시지 정보 포함 시 필요


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


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    # persona_id: int # PersonaResponse에 포함되므로 중복일 수 있음
    persona: PersonaResponse  # 대화 상대 페르소나 정보 포함
    created_at: datetime
    last_message_at: datetime
    # last_message_summary: Optional[ConversationLastMessageSummary] = None # 마지막 메시지 요약 (필요시)

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }
    # Pydantic V1
    # class Config:
    #     orm_mode = True
