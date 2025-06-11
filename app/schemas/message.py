# fastapi_backend/app/schemas/message.py
# Message 모델 관련 Pydantic 스키마

from datetime import datetime
from pydantic import Field

from app.models.message import SenderType  # Enum 임포트
from app.schemas.base_schema import BaseModel
from typing import List, Optional

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
class ChatMessageResponse(BaseModel):
    """메시지 전송 후 클라이언트에 반환될 최종 응답 스키마"""
    user_message: MessageResponse = Field(..., description="사용자가 보낸 메시지에 대한 DB 저장 결과")
    ai_message: MessageResponse = Field(..., description="AI가 응답한 메시지에 대한 DB 저장 결과")
    suggested_user_questions: List[str] = Field(..., description="사용자가 다음에 할 법한 질문 제안 목록")
    is_ready_to_move_on: bool = Field(..., description="다음 주제로 넘어갈 준비가 되었는지 여부")