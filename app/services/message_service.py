# app/services/message_service.py
import base64
import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.crud import crud_conversation, crud_message
from app.models.message import Message, SenderType
from app.models.message import Message as MessageModel
from app.models.user import User
from app.schemas.message import (
    ChatMessageResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.gemini_service import GeminiService
from app.services.s3_service import S3Service


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini_service = GeminiService()
        self.s3_service = S3Service()

    async def get_messages_for_conversation_admin(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
        sort_asc: bool = False,
    ) -> List[Message]:
        """[Admin] 특정 대화방의 메시지 목록을 가져옵니다."""
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        return await crud_message.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            sort_asc=sort_asc,
        )

    async def get_messages_for_conversation(
        self,
        conversation_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        sort_asc: bool = False,
    ) -> List[Message]:
        """특정 대화방의 메시지 목록을 가져옵니다 (사용자 권한 확인 포함)."""
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or you do not have access to this conversation.",
            )
        return await crud_message.get_messages_by_conversation(
            self.db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            sort_asc=sort_asc,
        )

    async def send_new_message(
        self, conversation_id: int, message_in: MessageCreate, current_user: User
    ) -> ChatMessageResponse:
        """대화방에 새 메시지를 전송하고 AI 응답을 받아 저장합니다."""

        # 1. 대화방 소유권 및 존재 여부 확인
        if current_user.is_superuser:
            db_conversation = await crud_conversation.get_conversation(
                self.db, conversation_id=conversation_id
            )
        else:
            db_conversation = await crud_conversation.get_conversation(
                self.db, conversation_id=conversation_id, user_id=current_user.id
            )

        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or not accessible.",
            )

        # 2. DB에 메시지를 저장하기 *전*에 현재까지의 대화 내역을 먼저 불러옵니다.
        history = await crud_message.get_messages_by_conversation(
            self.db, conversation_id=conversation_id, limit=None, sort_asc=True
        )

        # 3. Gemini AI에 먼저 응답을 요청합니다.
        # 이렇게 하면 history에는 이전 대화까지만 담기고, 현재 메시지는 user_message로 한 번만 전달됩니다.
        user_message_content = message_in.content if message_in.content else ""
        gemini_prompt_text = (
            "이 이미지는 어떤 내용이야? 자세히 설명해줘."
            if message_in.image_base64 and not user_message_content.strip()
            else user_message_content
        )

        try:
            (
                gemini_response,
                debug_contents,
            ) = await self.gemini_service.get_chat_response(
                system_prompt=db_conversation.persona.system_prompt,
                history=history,
                user_message=gemini_prompt_text,
                image_base64=message_in.image_base64,
                phishing_case=db_conversation.applied_phishing_case,
                starting_message=db_conversation.persona.starting_message,
            )
        except (ConnectionError, HTTPException) as e:
            detail = e.detail if isinstance(e, HTTPException) else str(e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
            )

        # 4. API 호출이 끝난 후, 사용자 메시지를 DB에 저장합니다.
        s3_image_key = None
        if message_in.image_base64:
            try:
                image_data = base64.b64decode(message_in.image_base64)
                filename = f"messages/{uuid.uuid4()}.png"
                await self.s3_service.upload_bytes_to_s3_async(
                    data_bytes=image_data, object_key=filename, content_type="image/png"
                )
                s3_image_key = filename
            except Exception as e:
                print(f"S3 이미지 업로드 실패: {e}")

        user_message_timestamp = datetime.now(timezone.utc)
        user_message_obj = MessageModel(
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
            content=user_message_content,
            image_key=s3_image_key,
            created_at=user_message_timestamp,
        )
        user_db_message = await crud_message.save_message(
            self.db, db_message=user_message_obj
        )
        db_conversation.last_message_at = user_db_message.created_at
        await crud_conversation.update_conversation(self.db, db_conv=db_conversation)

        # 5. 마지막으로 AI 응답 메시지를 DB에 저장합니다.
        ai_message_timestamp = datetime.now(timezone.utc)
        ai_message_obj = MessageModel(
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            content=gemini_response.response,
            gemini_token_usage=gemini_response.token_usage,
            created_at=ai_message_timestamp,
        )
        ai_db_message = await crud_message.save_message(
            self.db, db_message=ai_message_obj
        )
        db_conversation.last_message_at = ai_db_message.created_at
        await crud_conversation.update_conversation(self.db, db_conv=db_conversation)

        # 6. 최종 응답 객체 구성 및 반환
        return ChatMessageResponse(
            user_message=MessageResponse.model_validate(user_db_message),
            ai_message=MessageResponse.model_validate(ai_db_message),
            suggested_user_questions=gemini_response.suggested_user_questions,
            is_ready_to_move_on=gemini_response.progress_check.is_ready_to_move_on,
            debug_request_contents=debug_contents,
        )

    async def create_ai_message(
        self, conversation_id: int, content: str, token_usage: int = 0
    ) -> MessageModel:
        """
        AI가 보내는 시스템 메시지(예: 시작 메시지)를 생성하고 DB에 저장합니다.
        """
        # 1. AI 메시지의 타임스탬프를 명시적으로 생성합니다.
        ai_message_timestamp = datetime.now(timezone.utc)
        
        # 2. 타임스탬프를 포함하여 Message 객체를 직접 생성합니다.
        ai_message_obj = MessageModel(
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            content=content,
            gemini_token_usage=token_usage,
            created_at=ai_message_timestamp,
        )

        # 3. 단순화된 CRUD 함수를 통해 DB에 저장합니다.
        ai_message = await crud_message.save_message(
            self.db, db_message=ai_message_obj
        )

        # 4. 관련 대화방의 마지막 업데이트 시간을 갱신합니다.
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if conversation:
            conversation.last_message_at = ai_message.created_at
            await crud_conversation.update_conversation(self.db, db_conv=conversation)

        return ai_message