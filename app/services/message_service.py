# app/services/message_service.py
import base64
import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_conversation, crud_message
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
        """대화방에 새 메시지를 전송하고 AI 응답을 받습니다."""
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

        history = await crud_message.get_messages_by_conversation(
            self.db, conversation_id=conversation_id, limit=None, sort_asc=True
        )

        try:
            # ✅ content가 None일 경우를 대비하여 기본 텍스트를 설정합니다.
            user_message_content = message_in.content if message_in.content else ""

            # ✅ 이미지만 있고 텍스트가 없는 경우, AI에 전달할 기본 프롬프트를 추가합니다.
            #    이는 AI가 이미지의 맥락을 더 잘 이해하도록 돕습니다.
            if message_in.image_base64 and not user_message_content.strip():
                gemini_prompt_text = "이 이미지는 어떤 내용이야? 자세히 설명해줘."
            else:
                gemini_prompt_text = user_message_content

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

        s3_image_key = None
        if message_in.image_base64:
            try:
                image_data = base64.b64decode(message_in.image_base64)
                filename = f"messages/{uuid.uuid4()}.png"
                # 비동기 S3 업로드 함수를 사용합니다.
                await self.s3_service.upload_bytes_to_s3_async(
                    data_bytes=image_data, object_key=filename, content_type="image/png"
                )
                s3_image_key = filename
            except Exception as e:
                print(f"S3 이미지 업로드 실패: {e}")

        # ✅ MessageCreate 객체의 content가 None일 수 있으므로,
        #    미리 처리해둔 user_message_content를 사용합니다.
        #    이렇게 하면 crud_message.create_message 함수에 None이 전달되는 것을 방지합니다.
        user_message_to_save = MessageCreate(
            content=user_message_content,
            image_base64=message_in.image_base64,  # image_base64는 그대로 전달
        )

        user_db_message = await crud_message.create_message(
            self.db,
            message_in=user_message_to_save,
            conversation_id=conversation_id,
            sender_type=SenderType.USER,
            image_key=s3_image_key,
        )

        db_conversation.last_message_at = user_db_message.created_at
        await crud_conversation.update_conversation(self.db, db_conv=db_conversation)

        ai_message_in = MessageCreate(content=gemini_response.response)
        ai_db_message = await crud_message.create_message(
            self.db,
            message_in=ai_message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=gemini_response.token_usage,
        )

        db_conversation.last_message_at = ai_db_message.created_at
        await crud_conversation.update_conversation(self.db, db_conv=db_conversation)

        return ChatMessageResponse(
            user_message=MessageResponse.model_validate(user_db_message),
            ai_message=MessageResponse.model_validate(ai_db_message),
            suggested_user_questions=gemini_response.suggested_user_questions,
            is_ready_to_move_on=gemini_response.progress_check.is_ready_to_move_on,
            debug_request_contents=debug_contents,
        )

    async def create_ai_message(
        self, conversation_id: int, content: str, token_usage: int = 0
    ) -> Message:
        """AI 메시지를 생성하고 저장합니다."""
        message_in = MessageCreate(content=content)
        ai_message = await crud_message.create_message(
            self.db,
            message_in=message_in,
            conversation_id=conversation_id,
            sender_type=SenderType.AI,
            gemini_token_usage=token_usage,
        )

        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if conversation:
            conversation.last_message_at = ai_message.created_at
            await crud_conversation.update_conversation(self.db, db_conv=conversation)

        return ai_message
