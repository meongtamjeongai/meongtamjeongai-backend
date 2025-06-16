# fastapi_backend/app/crud/crud_message.py
# Message 모델에 대한 CRUD 작업을 위한 함수들

from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.message import Message, SenderType
from app.schemas.message import MessageCreate


def get_message(
    db: Session, message_id: int, conversation_id: Optional[int] = None
) -> Optional[Message]:
    """
    주어진 ID로 메시지를 조회합니다.
    conversation_id가 제공되면 해당 대화방의 메시지인지 확인합니다.
    """
    query = db.query(Message).filter(Message.id == message_id)
    if conversation_id:
        query = query.filter(Message.conversation_id == conversation_id)
    return query.first()


def get_messages_by_conversation(
    db: Session,
    *,
    conversation_id: int,
    skip: int = 0,
    limit: int | None = 100,
    sort_asc: bool = False,
) -> List[Message]:
    # ...
    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    if sort_asc:
        query = query.order_by(asc(Message.created_at))
    else:
        query = query.order_by(desc(Message.created_at))

    query = query.offset(skip)

    # ⭐️ limit이 None이 아닐 때만 limit을 적용
    if limit is not None:
        query = query.limit(limit)

    return query.all()


def create_message(
    db: Session,
    *,
    message_in: MessageCreate,
    conversation_id: int,
    sender_type: SenderType,
    gemini_token_usage: Optional[int] = None,
) -> Message:
    """
    새로운 메시지를 생성하고 특정 대화방에 추가합니다.
    """
    db_message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=message_in.content,  # MessageCreate 스키마에는 content만 있음
        gemini_token_usage=gemini_token_usage,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


# 메시지 수정 및 삭제는 일반적인 채팅 앱에서는 흔하지 않거나, 정책에 따라 다릅니다.
# def update_message(...) -> ...
# def delete_message(...) -> ...

# `app/crud/__init__.py` 파일에 다음을 추가합니다:
# from . import crud_message
