# fastapi_backend/app/schemas/message.py
# Message 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models.message import SenderType  # Enum 임포트
from app.schemas.base_schema import BaseModel


class MessageBase(BaseModel):
    content: str = Field(..., description="메시지 내용")


class MessageCreate(MessageBase):
    # conversation_id는 Path 파라미터로 받거나, 서비스 로직에서 설정
    # sender_type은 사용자 메시지 전송 시 'user'로 고정, AI 응답은 서버에서 'ai'로 설정
    # gemini_token_usage는 AI 응답 시 서버에서 설정
    pass


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    sender_type: SenderType
    gemini_token_usage: Optional[int] = None
    created_at: datetime

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }
    # Pydantic V1
    # class Config:
    #     orm_mode = True


# AI 응답과 함께 사용자 메시지도 반환하는 경우 (예시)
class ChatResponse(BaseModel):
    user_message: MessageResponse
    ai_response: MessageResponse
    # updated_user_points: Optional[int] = None # 포인트 차감 후 정보 (선택적)
