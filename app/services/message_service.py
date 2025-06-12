# fastapi_backend/app/services/message_service.py
# 메시지 관련 비즈니스 로직을 처리하는 서비스

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_message, crud_phishing
from app.models.message import Message, SenderType
from app.models.user import User
from app.schemas.gemini import GeminiChatResponse  # ⭐️ GeminiChatResponse 임포트
from app.schemas.message import (  # ⭐️ ChatMessageResponse 임포트
    ChatMessageResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.gemini_service import GeminiService


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()

    # 👇 관리자용 메시지 조회 서비스 추가
    def get_messages_for_conversation_admin(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_asc: bool = False,
    ) -> List[Message]:
        """
        [Admin] 특정 대화방의 메시지 목록을 가져옵니다 (사용자 권한 확인 없음).
        """
        conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        return crud_message.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            sort_asc=sort_asc,
        )

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
    ) -> ChatMessageResponse:
        # 1. 대화방 존재 및 사용자 접근 권한 확인
        db_conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or not accessible.",
            )

        # 2. 사용자 메시지를 DB에 저장
        user_db_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
        )
        # 대화방의 마지막 메시지 시간 업데이트
        crud_conversation.update_conversation_last_message_at(self.db, conversation_id)

        # 3. AI 응답 생성을 위한 준비
        # 전체 대화 기록을 시간순으로 가져오기
        history = crud_message.get_messages_by_conversation(
            self.db, conversation_id=conversation_id, limit=None, sort_asc=True
        )
        # 페르소나의 기본 시스템 프롬프트 가져오기
        system_prompt = db_conversation.persona.system_prompt

        # 대화 시작 시 랜덤 피싱 시나리오 가져오기
        random_phishing_case = None
        # 대화 기록에 사용자 메시지 하나만 있는 경우 (대화의 시작)
        if len(history) == 1:
            random_phishing_case = crud_phishing.get_random_phishing_case(self.db)
            if random_phishing_case:
                # (디버깅용) 어떤 시나리오가 로드되었는지 서버 로그에 출력
                print(
                    f"✅ [AI 시나리오] 피싱 사례 로드 성공 (ID: {random_phishing_case.id}, 제목: {random_phishing_case.title})"
                )
            else:
                print("⚠️ [AI 시나리오] 로드할 피싱 사례를 찾지 못했습니다.")

        # 4. Gemini 서비스를 호출하여 AI 응답 생성
        try:
            gemini_response: GeminiChatResponse = (
                await self.gemini_service.get_chat_response(
                    system_prompt=system_prompt,
                    history=history,
                    user_message=user_db_message.content,
                    # 조회된 피싱 사례를 Gemini 서비스로 전달
                    phishing_case=random_phishing_case,
                )
            )
        except (ConnectionError, HTTPException) as e:
            # Gemini 서비스 자체의 오류를 그대로 클라이언트에 전달
            detail = e.detail if isinstance(e, HTTPException) else str(e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
            )

        # 5. AI의 응답을 DB에 저장
        ai_message_in = MessageCreate(content=gemini_response.response)
        ai_db_message = crud_message.create_message(
            self.db,
            message_in=ai_message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=gemini_response.token_usage,
        )
        # 대화방의 마지막 메시지 시간 다시 업데이트
        crud_conversation.update_conversation_last_message_at(self.db, conversation_id)

        # 6. 최종 응답 객체를 생성하여 반환
        return ChatMessageResponse(
            user_message=MessageResponse.model_validate(user_db_message),
            ai_message=MessageResponse.model_validate(ai_db_message),
            suggested_user_questions=gemini_response.suggested_user_questions,
            is_ready_to_move_on=gemini_response.progress_check.is_ready_to_move_on,
        )

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
