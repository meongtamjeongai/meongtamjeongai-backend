# app/services/conversation_service.py
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_conversation, crud_persona, crud_phishing, crud_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationCreateAdmin
from app.services.message_service import MessageService
from app.services.s3_service import S3Service


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.s3_service = S3Service()
        self.message_service = MessageService(db)

    async def start_new_conversation_admin(
        self, conversation_in: ConversationCreateAdmin
    ) -> Conversation:
        """[Admin] 관리자가 특정 사용자와 페르소나를 지정하여 새 대화방을 시작합니다."""
        target_user = await crud_user.get_user(self.db, user_id=conversation_in.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {conversation_in.user_id} not found.",
            )

        create_data = ConversationCreate(
            persona_id=conversation_in.persona_id, title=conversation_in.title
        )
        return await self.start_new_conversation(
            conversation_in=create_data, current_user=target_user
        )

    async def get_all_conversations_admin(
        self, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """[Admin] 시스템의 모든 대화방 목록을 조회합니다."""
        return await crud_conversation.get_all_conversations(self.db, skip=skip, limit=limit)

    async def delete_conversation_admin(self, conversation_id: int) -> Optional[Conversation]:
        """[Admin] 특정 대화방을 ID로 삭제합니다."""
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        messages_to_delete = await self.message_service.get_messages_for_conversation_admin(
            conversation_id=conversation_id, limit=None
        )

        for message in messages_to_delete:
            if message.image_key:
                try:
                    self.s3_service.delete_object(object_key=message.image_key)
                except Exception as e:
                    print(f"S3 이미지 삭제 실패 (Key: {message.image_key}): {e}")

        return await crud_conversation.delete_conversation_by_id(
            self.db, conversation_id=conversation_id
        )

    async def get_conversation_by_id_for_user(
        self, conversation_id: int, current_user: User
    ) -> Optional[Conversation]:
        """ID로 특정 대화방을 조회 (사용자 권한 확인 포함)"""
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or not accessible",
            )
        return conversation

    async def get_all_conversations_for_user(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """현재 사용자의 모든 대화방 목록을 조회"""
        return await crud_conversation.get_conversations_by_user(
            self.db, user_id=current_user.id, skip=skip, limit=limit
        )

    async def start_new_conversation(
        self, conversation_in: ConversationCreate, current_user: User
    ) -> Conversation:
        """새로운 대화방을 시작합니다."""
        persona = await crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        new_conversation = await crud_conversation.create_conversation(
            self.db, conversation_in=conversation_in, user_id=current_user.id
        )

        random_case = await crud_phishing.get_random_phishing_case(self.db)
        if random_case:
            new_conversation.applied_phishing_case_id = random_case.id
            await crud_conversation.update_conversation(self.db, db_conv=new_conversation)

        if persona.starting_message:
            await self.message_service.create_ai_message(
                conversation_id=new_conversation.id,
                content=persona.starting_message,
            )

        return new_conversation

    async def delete_existing_conversation(
        self, conversation_id: int, current_user: User
    ) -> Optional[Conversation]:
        """대화방을 삭제합니다 (사용자 권한 확인 포함)."""
        conversation_to_delete = await self.get_conversation_by_id_for_user(
            conversation_id=conversation_id, current_user=current_user
        )
        return await crud_conversation.delete_conversation(
            self.db, conversation_id=conversation_to_delete.id
        )
