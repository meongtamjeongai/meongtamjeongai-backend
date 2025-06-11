# fastapi_backend/app/crud/crud_conversation.py
# Conversation 모델에 대한 CRUD 작업을 위한 함수들

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation
from app.schemas.conversation import (
    ConversationCreate,  # ConversationUpdate는 선택적이므로 우선 Create만
)


def get_conversation(
    db: Session, conversation_id: int, user_id: Optional[int] = None
) -> Optional[Conversation]:
    """
    주어진 ID로 대화방을 조회합니다.
    user_id가 제공되면 해당 사용자의 대화방인지 확인합니다.
    """
    query = db.query(Conversation).filter(Conversation.id == conversation_id)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    return query.first()


def get_conversations_by_user(
    db: Session, *, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """
    특정 사용자의 모든 대화방 목록을 최신 메시지 시간 순으로 정렬하여 조회합니다.
    페르소나 정보도 함께 로드합니다.
    """
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(joinedload(Conversation.persona))  # 페르소나 정보 Eager 로딩
        .order_by(desc(Conversation.last_message_at))  # 최신 메시지 시간 순 정렬
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_conversation(
    db: Session, *, conversation_in: ConversationCreate, user_id: int
) -> Conversation:
    """
    새로운 대화방을 생성합니다.
    user_id와 persona_id는 필수입니다.
    """
    # 동일 user_id와 persona_id로 여러 대화방 생성 가능 (요구사항)
    # 만약 title이 제공되지 않으면 기본값 설정 또는 서비스 계층에서 처리 가능

    db_conversation_data = conversation_in.model_dump(exclude_unset=True)
    db_conversation = Conversation(**db_conversation_data, user_id=user_id)

    # title이 명시적으로 None으로 오거나, 아예 오지 않았을 때 기본값 설정 (선택적)
    if db_conversation.title is None:
        # 서비스 계층에서 페르소나 이름을 가져와 설정하는 것이 더 적절할 수 있음
        # 여기서는 간단히 None으로 두거나, 임시 제목 설정 가능
        # db_conversation.title = f"Conversation with Persona {conversation_in.persona_id}"
        pass

    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def update_conversation_last_message_at(
    db: Session, conversation_id: int
) -> Optional[Conversation]:
    """대화방의 last_message_at을 현재 시간으로 업데이트합니다."""
    db_conversation = get_conversation(db, conversation_id=conversation_id)
    if db_conversation:
        # last_message_at은 onupdate=func.now()로 자동 업데이트되므로,
        # 실제로는 객체를 한번 더 저장(add, commit)하거나,
        # 명시적으로 시간을 바꿔주고 저장해야 할 수 있습니다.
        # 여기서는 모델의 onupdate에 의존한다고 가정하거나, 명시적으로 업데이트합니다.
        # from sqlalchemy import func
        # db_conversation.last_message_at = func.now() # 이렇게 하면 DB 함수가 실행됨
        # 또는 Python datetime 사용 후 commit
        from datetime import datetime, timezone

        db_conversation.last_message_at = datetime.now(timezone.utc)
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation
    return None


def delete_conversation(
    db: Session, *, conversation_id: int, user_id: int
) -> Optional[Conversation]:
    """
    주어진 ID의 대화방을 삭제합니다.
    해당 사용자의 대화방인지 확인 후 삭제합니다.
    """
    db_conversation = get_conversation(
        db, conversation_id=conversation_id, user_id=user_id
    )
    if db_conversation:
        db.delete(db_conversation)
        db.commit()
        return db_conversation
    return None


# 👇 관리자용 전체 대화방 조회 함수 추가
def get_all_conversations(
    db: Session, *, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """
    모든 대화방 목록을 최신 메시지 시간 순으로 정렬하여 조회합니다.
    페르소나와 사용자 정보도 함께 로드합니다. (관리자용)
    """
    return (
        db.query(Conversation)
        .options(
            joinedload(Conversation.persona),  # 페르소나 정보 Eager 로딩
            joinedload(Conversation.user),  # 👈 사용자 정보 Eager 로딩 추가
        )
        .order_by(desc(Conversation.last_message_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


# 👇 관리자용 대화방 삭제 함수 추가
def delete_conversation_by_id(
    db: Session, *, conversation_id: int
) -> Optional[Conversation]:
    """
    주어진 ID의 대화방을 삭제합니다. (관리자용, 사용자 권한 확인 없음)
    """
    db_conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if db_conversation:
        db.delete(db_conversation)
        db.commit()
        return db_conversation
    return None
