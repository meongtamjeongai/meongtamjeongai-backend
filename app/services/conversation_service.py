# fastapi_backend/app/services/conversation_service.py
# 대화방 관련 비즈니스 로직을 처리하는 서비스

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_persona, crud_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationCreateAdmin
from app.services.message_service import MessageService


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    # 👇 관리자용 대화방 생성 서비스 함수
    def start_new_conversation_admin(
        self, conversation_in: ConversationCreateAdmin
    ) -> Conversation:
        """[Admin] 관리자가 특정 사용자와 페르소나를 지정하여 새 대화방을 시작합니다."""
        # 1. 대상 사용자가 존재하는지 확인
        user = crud_user.get_user(self.db, user_id=conversation_in.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {conversation_in.user_id} not found.",
            )

        # 2. 대상 페르소나가 존재하는지 확인
        persona = crud_persona.get_persona(
            self.db, persona_id=conversation_in.persona_id
        )
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with id {conversation_in.persona_id} not found.",
            )

        # 3. ConversationCreate 스키마 형태로 변환하여 기존 생성 함수 호출
        #    (이렇게 하면 코드 재사용성이 높아집니다)
        create_data = ConversationCreate(
            persona_id=conversation_in.persona_id, title=conversation_in.title
        )

        new_conversation = crud_conversation.create_conversation(
            self.db, conversation_in=create_data, user_id=conversation_in.user_id
        )

        return new_conversation

    # 👇 관리자용 전체 대화방 조회 서비스 추가
    def get_all_conversations_admin(
        self, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """[Admin] 시스템의 모든 대화방 목록을 조회합니다."""
        return crud_conversation.get_all_conversations(self.db, skip=skip, limit=limit)

    # 👇 관리자용 대화방 삭제 서비스 추가
    def delete_conversation_admin(self, conversation_id: int) -> Optional[Conversation]:
        """[Admin] 특정 대화방을 ID로 삭제합니다."""
        conversation_to_delete = crud_conversation.delete_conversation_by_id(
            self.db, conversation_id=conversation_id
        )
        if not conversation_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation_to_delete

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

        # 3. 페르소나에 시작 메시지가 정의되어 있으면, 대화방의 첫 메시지로 추가
        if persona.starting_message:
            # MessageService 인스턴스를 생성
            message_service = MessageService(self.db)

            # 시스템(또는 AI) 메시지로 시작 메시지를 생성합니다.
            # sender_type을 'ai'로 하면 채팅 UI에서 AI의 말풍선으로 보입니다.
            message_service.create_ai_message(
                conversation_id=new_conversation.id,
                content=persona.starting_message,
            )
            print(
                f"✅ Conversation(id:{new_conversation.id})에 시작 메시지를 추가했습니다."
            )

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
