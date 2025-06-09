# fastapi_backend/app/services/message_service.py
# 메시지 관련 비즈니스 로직을 처리하는 서비스

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_message  # UserPoint CRUD 추가
from app.models.message import Message, SenderType
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse  # MessageResponse 추가

# from app.services.gemini_service import GeminiService # Gemini AI 연동 시 (별도 서비스)


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        # self.gemini_service = GeminiService() # Gemini 서비스 초기화 (필요시)

    def get_messages_for_conversation(
        self,
        conversation_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        sort_asc: bool = False,
    ) -> List[Message]:
        """
        특정 대화방의 메시지 목록을 가져옵니다 (사용자 권한 확인 포함).
        """
        # 1. 대화방 존재 및 사용자 접근 권한 확인
        conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or you do not have access to this conversation.",
            )

        return crud_message.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            sort_asc=sort_asc,
        )

    async def send_new_message(
        self, conversation_id: int, message_in: MessageCreate, current_user: User
    ) -> List[
        MessageResponse
    ]:  # 사용자 메시지와 AI 응답을 함께 반환 (ChatResponse 스키마 또는 List[MessageResponse])
        """
        사용자가 새 메시지를 전송하면, 이를 저장하고 AI의 응답도 생성하여 저장합니다.
        사용자 메시지와 AI 응답 메시지를 함께 반환합니다.
        """
        # 1. 대화방 존재 및 사용자 접근 권한 확인
        db_conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or you do not have access to this conversation.",
            )

        # (선택) 사용자 포인트 차감 로직 (실제 Gemini API 호출 전에)
        # user_point = crud_user_point.get_user_point(self.db, user_id=current_user.id)
        # if not user_point or user_point.points < 1: # 예시: 메시지당 1포인트 차감
        #     raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Not enough points to send a message.")
        # crud_user_point.update_user_point(self.db, user_id=current_user.id, points_to_deduct=1) # 포인트 차감

        # 2. 사용자 메시지 저장
        user_db_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
        )

        # 3. 대화방의 last_message_at 업데이트
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )

        # 4. Gemini AI 응답 생성 (여기서는 임시로 에코 또는 고정 메시지)
        # TODO: 실제 Gemini API 연동 로직으로 대체
        # system_prompt = db_conversation.persona.system_prompt
        # ai_response_content, token_usage = await self.gemini_service.get_chat_response(
        #     system_prompt=system_prompt,
        #     user_message=user_db_message.content,
        #     # 이전 대화 내용 전달 (필요시)
        #     # history=crud_message.get_messages_by_conversation(self.db, conversation_id=conversation_id, limit=10, sort_asc=True)
        # )

        ai_response_content = (
            f"AI 응답: '{user_db_message.content}'라고 하셨군요!"  # 임시 에코
        )
        token_usage = 10  # 임시 토큰 사용량

        # 5. AI 응답 메시지 저장
        ai_message_in = MessageCreate(content=ai_response_content)
        ai_db_message = crud_message.create_message(
            self.db,
            message_in=ai_message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=token_usage,
        )

        # 6. 대화방의 last_message_at 다시 업데이트 (AI 메시지 후)
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )

        # MessageResponse 스키마로 변환하여 반환
        # SQLAlchemy 모델 객체를 Pydantic 스키마로 변환 시 from_attributes=True (또는 orm_mode=True) 설정 필요
        user_message_response = MessageResponse.model_validate(
            user_db_message
        )  # Pydantic v2
        ai_message_response = MessageResponse.model_validate(
            ai_db_message
        )  # Pydantic v2
        # Pydantic v1: user_message_response = MessageResponse.from_orm(user_db_message)
        # Pydantic v1: ai_message_response = MessageResponse.from_orm(ai_db_message)

        return [user_message_response, ai_message_response]

    def create_system_message(self, conversation_id: int, content: str) -> Message:
        """
        시스템 메시지를 생성하고 저장합니다 (예: "대화방이 시작되었습니다.").
        """
        message_in = MessageCreate(content=content)
        system_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.SYSTEM,
        )
        # 시스템 메시지 생성 후에도 last_message_at 업데이트
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )
        return system_message


# `app/services/__init__.py` 파일에 다음을 추가합니다:
# from .message_service import MessageService
# __all__.append("MessageService")
