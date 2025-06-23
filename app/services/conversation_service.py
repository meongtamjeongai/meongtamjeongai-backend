# app/services/conversation_service.py
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    crud_conversation,
    crud_persona,
    crud_phishing,
    crud_user,
)
from app.models.conversation import Conversation
from app.models.persona import Persona
from app.models.phishing_case import PhishingCase
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationCreateAdmin,
    ConversationCreateWithCategory,
)
from app.schemas.phishing import PhishingCaseCreate
from app.services.gemini_service import GeminiService
from app.services.message_service import MessageService
from app.services.s3_service import S3Service


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.s3_service = S3Service()
        self.message_service = MessageService(db)
        self.gemini_service = GeminiService()

    async def _get_or_create_phishing_case(
        self, category_code: Optional[str] = None, force_ai_creation: bool = False
    ) -> Optional[PhishingCase]:
        """
        피싱 사례를 가져오거나 생성하는 로직을 담당하는 내부 헬퍼.
        - category_code가 없으면: 전체에서 랜덤으로 조회
        - category_code가 있으면: 해당 카테고리에서 랜덤으로 조회
        - force_ai_creation=True이면: DB 조회 없이 항상 AI로 생성
        """
        # 항상 AI로 생성해야 하는 경우
        if force_ai_creation:
            if not category_code:
                raise ValueError("AI case creation requires a category_code.")

            category_obj = await crud_phishing.get_category_by_code(
                self.db, code=category_code
            )
            if not category_obj:
                raise HTTPException(
                    status_code=404, detail=f"Category '{category_code}' not found."
                )

            print(
                f"🤖 Always generating a new phishing case with AI for category '{category_code}'..."
            )
            generated_data = (
                await self.gemini_service.generate_phishing_case_on_the_fly(
                    category=category_obj
                )
            )

            case_to_create = PhishingCaseCreate(
                category_code=category_code,
                title=generated_data.title,
                content=generated_data.content,
            )
            return await crud_phishing.create_phishing_case(
                self.db, case_in=case_to_create
            )

        # DB에서 조회 (카테고리 지정 또는 전체)
        phishing_case = await crud_phishing.get_random_phishing_case(
            self.db, category_code=category_code
        )

        # DB에 없었고, 카테고리가 지정되었다면 AI로 생성
        if not phishing_case and category_code:
            category_obj = await crud_phishing.get_category_by_code(
                self.db, code=category_code
            )
            if not category_obj:
                raise HTTPException(
                    status_code=404, detail=f"Category '{category_code}' not found."
                )

            print(
                f"⚠️ No phishing case found for category '{category_code}'. Generating one with AI..."
            )
            generated_data = (
                await self.gemini_service.generate_phishing_case_on_the_fly(
                    category=category_obj
                )
            )

            case_to_create = PhishingCaseCreate(
                category_code=category_code,
                title=generated_data.title,
                content=generated_data.content,
            )
            return await crud_phishing.create_phishing_case(
                self.db, case_in=case_to_create
            )

        return phishing_case

    async def _create_conversation_base(
        self,
        persona: Persona,
        current_user: User,
        title: Optional[str],
        phishing_case: Optional[PhishingCase],
    ) -> Conversation:
        """대화방 생성의 공통 절차를 수행하는 내부 헬퍼."""
        # 1. 기본 대화방 생성
        base_conv_data = ConversationCreate(persona_id=persona.id, title=title)
        new_conversation = await crud_conversation.create_conversation(
            self.db, conversation_in=base_conv_data, user_id=current_user.id
        )

        # 2. 피싱 사례 적용
        if phishing_case:
            new_conversation.applied_phishing_case_id = phishing_case.id
            new_conversation = await crud_conversation.update_conversation(
                self.db, db_conv=new_conversation
            )

        # 3. 시작 메시지 전송
        if persona.starting_message:
            await self.message_service.create_ai_message(
                conversation_id=new_conversation.id,
                content=persona.starting_message,
            )

        return new_conversation

    async def start_new_conversation(
        self, conversation_in: ConversationCreate, current_user: User
    ) -> Conversation:
        """새로운 대화방을 시작합니다. (랜덤 피싱 사례 적용)"""
        persona = await crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=404,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        # 로직 위임: 전체 랜덤 사례 조회
        phishing_case = await self._get_or_create_phishing_case()

        return await self._create_conversation_base(
            persona=persona,
            current_user=current_user,
            title=conversation_in.title,
            phishing_case=phishing_case,
        )

    async def start_conversation_with_category(
        self, conversation_in: ConversationCreateWithCategory, current_user: User
    ) -> Conversation:
        """특정 피싱 카테고리를 지정하여 새 대화방을 시작합니다. (DB 우선)"""
        persona = await crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=404,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        # 로직 위임: 카테고리 지정하여 조회/생성
        phishing_case = await self._get_or_create_phishing_case(
            category_code=conversation_in.category_code.value
        )

        return await self._create_conversation_base(
            persona=persona,
            current_user=current_user,
            title=conversation_in.title,
            phishing_case=phishing_case,
        )

    async def start_conversation_with_ai_case(
        self, conversation_in: ConversationCreateWithCategory, current_user: User
    ) -> Conversation:
        """항상 AI가 새로 생성한 피싱 사례를 적용하여 대화방을 시작합니다."""
        persona = await crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=404,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        # 로직 위임: 카테고리 지정 + AI 강제 생성
        phishing_case = await self._get_or_create_phishing_case(
            category_code=conversation_in.category_code.value, force_ai_creation=True
        )

        return await self._create_conversation_base(
            persona=persona,
            current_user=current_user,
            title=conversation_in.title,
            phishing_case=phishing_case,
        )

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
        return await crud_conversation.get_all_conversations(
            self.db, skip=skip, limit=limit
        )

    async def delete_conversation_admin(
        self, conversation_id: int
    ) -> Optional[Conversation]:
        """[Admin] 특정 대화방을 ID로 삭제합니다."""
        conversation = await crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        messages_to_delete = (
            await self.message_service.get_messages_for_conversation_admin(
                conversation_id=conversation_id, limit=None
            )
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
