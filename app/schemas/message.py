# fastapi_backend/app/schemas/message.py
# Message 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator

from app.models.message import SenderType  # Enum 임포트
from app.schemas.base_schema import BaseModel


class MessageBase(BaseModel):
    content: str = Field(..., description="메시지 내용")


class MessageCreate(MessageBase):
    content: Optional[str] = Field(None, description="메시지 내용")
    image_base64: Optional[str] = Field(None, description="Base64-encoded image data")

    @model_validator(mode="after")
    def check_content_or_image_exists(self) -> "MessageCreate":
        """
        content와 image_base64 필드 중 적어도 하나는 값이 있는지 확인합니다.
        """
        if (not self.content or not self.content.strip()) and not self.image_base64:
            raise ValueError("Either 'content' or 'image_base64' must be provided.")
        return self


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    sender_type: SenderType
    gemini_token_usage: Optional[int] = None
    created_at: datetime
    image_key: Optional[str] = None

    model_config = {"from_attributes": True}


# AI 응답과 함께 사용자 메시지도 반환하는 경우 (예시)
class ChatMessageResponse(BaseModel):
    """메시지 전송 후 클라이언트에 반환될 최종 응답 스키마"""

    user_message: MessageResponse = Field(
        ..., description="사용자가 보낸 메시지에 대한 DB 저장 결과"
    )
    ai_message: MessageResponse = Field(
        ..., description="AI가 응답한 메시지에 대한 DB 저장 결과"
    )
    suggested_user_questions: List[str] = Field(
        ..., description="사용자가 다음에 할 법한 질문 제안 목록(최대 3개)"
    )
    is_ready_to_move_on: bool = Field(
        ..., description="다음 주제로 넘어갈 준비가 되었는지 여부"
    )
    debug_request_contents: Optional[List[Dict[str, Any]]] = Field(
        None, description="디버깅용: 토큰 계산에 사용된 실제 요청 컨텐츠"
    )
