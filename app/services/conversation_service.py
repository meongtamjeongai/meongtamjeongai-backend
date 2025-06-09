# fastapi_backend/app/services/conversation_service.py
# 대화방 관련 비즈니스 로직을 처리하는 서비스

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_persona
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def get_conversation_by_id_for_user(
        self, conversation_id: int, current_user: User
    ) -> Optional[Conversation]:
        """ID로 특정 대화방을 조회 (사용자 권한 확인 포함)"""
        conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or not accessible",
            )
        return conversation

    def get_all_conversations_for_user(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """현재 사용자의 모든 대화방 목록을 조회"""
        return crud_conversation.get_conversations_by_user(
            self.db, user_id=current_user.id, skip=skip, limit=limit
        )

    def start_new_conversation(
        self, conversation_in: ConversationCreate, current_user: User
    ) -> Conversation:
        """
        새로운 대화방을 시작합니다.
        persona_id가 유효한지 확인합니다.
        """
        # 1. 페르소나 존재 확인
        persona = crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        # (선택적) 공개 페르소나가 아니면서, 해당 페르소나 생성자가 현재 유저가 아니라면 접근 제한
        # if not persona.is_public and (persona.created_by_user_id != current_user.id):
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot start conversation with this persona.")

        # 2. 대화방 제목 자동 생성 (만약 비어있다면)
        if not conversation_in.title:
            # TODO: 동일 유저, 동일 페르소나로 생성된 대화방 개수를 세서 제목에 넘버링 가능
            # count = # (self.db.query(Conversation).filter_by(user_id=current_user.id, persona_id=persona.id).count()) + 1
            # conversation_in.title = f"{persona.name}님과의 대화" # 간단한 제목
            pass  # 우선은 스키마 기본값이나 None 유지

        new_conversation = crud_conversation.create_conversation(
            self.db, conversation_in=conversation_in, user_id=current_user.id
        )

        # (선택) 대화방 생성 시 시스템 메시지 추가 로직 (MessageService에서 처리)
        # message_service = MessageService(self.db)
        # message_service.create_system_message(conversation_id=new_conversation.id, content="대화방이 시작되었습니다.")

        return new_conversation

    def delete_existing_conversation(
        self, conversation_id: int, current_user: User
    ) -> Optional[Conversation]:
        """
        대화방을 삭제합니다 (사용자 권한 확인 포함).
        실제로는 하위 메시지들도 함께 삭제됩니다 (모델의 cascade 설정 덕분).
        """
        # get_conversation_by_id_for_user 에서 이미 권한 확인 및 404 처리
        conversation_to_delete = self.get_conversation_by_id_for_user(
            conversation_id=conversation_id, current_user=current_user
        )
        # 위에서 conversation이 없으면 HTTPException 발생하므로, 여기서는 항상 객체가 있다고 가정.

        return crud_conversation.delete_conversation(
            self.db, conversation_id=conversation_to_delete.id, user_id=current_user.id
        )


# `app/services/__init__.py` 파일에 다음을 추가합니다:
# from .conversation_service import ConversationService
# __all__.append("ConversationService")
