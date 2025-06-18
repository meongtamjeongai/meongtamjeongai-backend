# fastapi_backend/app/services/message_service.py
# 메시지 관련 비즈니스 로직을 처리하는 서비스

from typing import List
import base64
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_message, crud_phishing
from app.models.message import Message, SenderType
from app.models.user import User

from app.schemas.message import (
    ChatMessageResponse,
    MessageCreate,
    MessageResponse,
)

from app.services.gemini_service import GeminiService
from app.services.s3_service import S3Service


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        self.s3_service = S3Service()

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

        # 2. AI 응답 생성을 위한 준비
        history = crud_message.get_messages_by_conversation(
            self.db, conversation_id=conversation_id, limit=None, sort_asc=True
        )
        persona = db_conversation.persona
        system_prompt = persona.system_prompt
        starting_message = persona.starting_message
        phishing_case_to_apply = db_conversation.applied_phishing_case
        if phishing_case_to_apply is None:
            random_case = crud_phishing.get_random_phishing_case(self.db)
            if random_case:
                db_conversation.applied_phishing_case_id = random_case.id
                self.db.add(db_conversation)
                self.db.commit()
                self.db.refresh(db_conversation)
                phishing_case_to_apply = db_conversation.applied_phishing_case

        # --- ✅ 3. Gemini 서비스 호출하여 AI 응답 생성 (DB 저장 전) ---
        try:
            (
                gemini_response,
                debug_contents,
            ) = await self.gemini_service.get_chat_response(
                system_prompt=system_prompt,
                history=history,
                user_message=message_in.content,
                image_base64=message_in.image_base64,  # 이미지 데이터 전달
                phishing_case=phishing_case_to_apply,
                starting_message=starting_message,
            )
        except (ConnectionError, HTTPException) as e:
            detail = e.detail if isinstance(e, HTTPException) else str(e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
            )

        # --- ✅ 4. AI 응답 성공 후, 이미지 S3 업로드 및 사용자 메시지 DB 저장 ---
        s3_image_key = None
        if message_in.image_base64:
            try:
                image_data = base64.b64decode(message_in.image_base64)
                # 파일명은 UUID로 생성하여 고유성 보장
                filename = f"messages/{uuid.uuid4()}.png"
                self.s3_service.upload_bytes_to_s3(
                    data_bytes=image_data, object_key=filename, content_type="image/png"
                )
                s3_image_key = filename
            except Exception as e:
                # S3 업로드 실패 시, 로깅하고 이미지 없이 메시지만 저장
                print(f"S3 이미지 업로드 실패: {e}")
                # 이 경우 s3_image_key는 None으로 유지됨

        # DB에 사용자 메시지 저장 (s3_image_key 포함)
        user_db_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
            # --- ✅ image_key 전달 ---
            image_key=s3_image_key,
        )

        # 대화방 마지막 메시지 시간 업데이트
        crud_conversation.update_conversation_last_message_at(self.db, conversation_id)

        # 5. AI의 응답을 DB에 저장
        ai_message_in = MessageCreate(content=gemini_response.response)
        ai_db_message = crud_message.create_message(
            self.db,
            message_in=ai_message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=gemini_response.token_usage,
        )

        crud_conversation.update_conversation_last_message_at(self.db, conversation_id)

        # 6. 최종 응답 객체를 생성하여 반환
        return ChatMessageResponse(
            user_message=MessageResponse.model_validate(user_db_message),
            ai_message=MessageResponse.model_validate(ai_db_message),
            suggested_user_questions=gemini_response.suggested_user_questions,
            is_ready_to_move_on=gemini_response.progress_check.is_ready_to_move_on,
            debug_request_contents=debug_contents,
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

    def create_ai_message(self, conversation_id: int, content: str, token_usage: int = 0) -> Message:
        """
        AI 메시지를 생성하고 저장합니다. 시작 메시지 등에 사용됩니다.
        """
        message_in = MessageCreate(content=content)
        ai_message = crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=token_usage,
        )
        # AI 메시지 생성 후에도 last_message_at 업데이트
        crud_conversation.update_conversation_last_message_at(
            self.db, conversation_id=conversation_id
        )
        return ai_message

# `app/services/__init__.py` 파일에 다음을 추가합니다:
# from .message_service import MessageService
# __all__.append("MessageService")
