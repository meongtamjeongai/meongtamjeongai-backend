# fastapi_backend/app/services/conversation_service.py
# 대화방 관련 비즈니스 로직을 처리하는 서비스

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_conversation, crud_persona, crud_phishing, crud_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationCreateAdmin
from app.services.message_service import MessageService
from app.services.s3_service import S3Service


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.s3_service = S3Service()
        self.message_service = MessageService(db)

    # 👇 관리자용 대화방 생성 서비스 함수
    def start_new_conversation_admin(
        self, conversation_in: ConversationCreateAdmin
    ) -> Conversation:
        """
        [Admin] 관리자가 특정 사용자와 페르소나를 지정하여 새 대화방을 시작합니다.
        내부적으로 일반 사용자용 대화방 생성 함수를 호출하여 로직을 재사용합니다.
        """
        # 1. 대상 사용자가 존재하는지 확인합니다.
        target_user = crud_user.get_user(self.db, user_id=conversation_in.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {conversation_in.user_id} not found.",
            )

        # 2. ConversationCreate 스키마 형태로 변환합니다.
        #    이 스키마는 start_new_conversation 함수가 요구하는 입력 형식입니다.
        create_data = ConversationCreate(
            persona_id=conversation_in.persona_id, title=conversation_in.title
        )

        # 3. 일반 사용자용 대화방 생성 함수를 호출합니다.
        #    이때, current_user 인자에는 관리자가 지정한 '대상 사용자'를 전달합니다.
        #    이렇게 하면 피싱 사례 할당, 시작 메시지 추가 등의 모든 로직이 재사용됩니다.
        return self.start_new_conversation(
            conversation_in=create_data, current_user=target_user
        )

    # 👇 관리자용 전체 대화방 조회 서비스 추가
    def get_all_conversations_admin(
        self, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """[Admin] 시스템의 모든 대화방 목록을 조회합니다."""
        return crud_conversation.get_all_conversations(self.db, skip=skip, limit=limit)

    # 👇 관리자용 대화방 삭제 서비스 수정
    def delete_conversation_admin(self, conversation_id: int) -> Optional[Conversation]:
        """
        [Admin] 특정 대화방을 ID로 삭제합니다.
        삭제 전, 해당 대화방에 속한 모든 메시지의 S3 이미지를 함께 삭제합니다.
        """
        # 1. 삭제할 대화방이 존재하는지 확인합니다.
        conversation = crud_conversation.get_conversation(
            self.db, conversation_id=conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # 2. 대화방에 속한 모든 메시지를 가져옵니다.
        # 페이지네이션 없이 모든 메시지를 가져오기 위해 limit=None을 사용합니다.
        messages_to_delete = self.message_service.get_messages_for_conversation_admin(
            conversation_id=conversation_id, limit=None
        )

        # 3. 각 메시지를 순회하며 연결된 S3 이미지가 있으면 삭제합니다.
        for message in messages_to_delete:
            if message.image_key:
                try:
                    print(f"S3 이미지 삭제 시도: {message.image_key}")
                    self.s3_service.delete_object(object_key=message.image_key)
                except Exception as e:
                    # S3 삭제 실패 시, 에러를 로깅하고 계속 진행할지 또는 전체 작업을 중단할지 결정해야 합니다.
                    # 여기서는 에러를 로깅하고 계속 진행하여 DB 데이터는 삭제되도록 합니다.
                    print(f"S3 이미지 삭제 실패 (Key: {message.image_key}): {e}")

        # 4. 모든 S3 리소스 정리 후, DB에서 대화방을 삭제합니다.
        # Conversation 모델의 cascade 설정에 의해 하위 메시지들도 함께 삭제됩니다.
        deleted_conversation = crud_conversation.delete_conversation_by_id(
            self.db, conversation_id=conversation_id
        )

        return deleted_conversation

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

        random_case = crud_phishing.get_random_phishing_case(self.db)
        if random_case:
            new_conversation.applied_phishing_case_id = random_case.id
            self.db.add(new_conversation)
            self.db.commit()
            self.db.refresh(new_conversation)
            print(
                f"✅ 대화방(ID:{new_conversation.id}) 생성 시 피싱 사례(ID:{random_case.id}) 할당 완료"
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
