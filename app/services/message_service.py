# fastapi_backend/app/services/message_service.py
# 메시지 관련 비즈니스 로직을 처리하는 서비스

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_message  # UserPoint CRUD 추가
from app.models.message import Message, SenderType
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse  # MessageResponse 추가

from app.services.gemini_service import GeminiService


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()

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
    ) -> List[MessageResponse]:
        # 1. 대화방 존재 및 권한 확인 (기존과 동일)
        db_conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or not accessible.",
            )

        # 2. 사용자 메시지 저장 (기존과 동일)
        user_db_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
        )

        # 3. 대화방의 last_message_at 업데이트 (기존과 동일)
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )

        # ⭐️ 4. Gemini AI 응답 생성
        # 이전 대화 기록을 DB에서 가져옴
        history = crud_message.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            limit=None, # 👈 limit=None으로 설정하여 전체 기록을 가져옴
            sort_asc=True # 👈 채팅 기록은 시간 순서(오름차순)가 중요
        )
        
        # 페르소나의 시스템 프롬프트 가져오기
        system_prompt = db_conversation.persona.system_prompt

        # GeminiService 호출
        ai_response_content, token_usage = await self.gemini_service.get_chat_response(
            system_prompt=system_prompt,
            history=history,
            user_message=user_db_message.content
        )

        # 5. AI 응답 메시지 저장 (토큰 사용량 포함)
        ai_message_in = MessageCreate(content=ai_response_content)
        ai_db_message = crud_message.create_message(
            self.db,
            message_in=ai_message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=token_usage, # 👈 토큰 사용량 저장
        )

        # 6. 대화방의 last_message_at 다시 업데이트 (기존과 동일)
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )

        # 7. 최종 결과 반환 (기존과 동일)
        user_message_response = MessageResponse.model_validate(user_db_message)
        ai_message_response = MessageResponse.model_validate(ai_db_message)

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
