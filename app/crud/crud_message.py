# app/crud/crud_message.py
from typing import List, Optional

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, SenderType
from app.schemas.message import MessageCreate


async def get_message(
    db: AsyncSession, message_id: int, conversation_id: Optional[int] = None
) -> Optional[Message]:
    """주어진 ID로 메시지를 조회합니다."""
    stmt = select(Message).where(Message.id == message_id)
    if conversation_id:
        stmt = stmt.where(Message.conversation_id == conversation_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_messages_by_conversation(
    db: AsyncSession,
    *,
    conversation_id: int,
    skip: int = 0,
    limit: int | None = 100,
    sort_asc: bool = False,
) -> List[Message]:
    """특정 대화방의 메시지 목록을 조회합니다."""
    stmt = select(Message).where(Message.conversation_id == conversation_id)

    if sort_asc:
        stmt = stmt.order_by(asc(Message.created_at))
    else:
        stmt = stmt.order_by(desc(Message.created_at))

    stmt = stmt.offset(skip)

    if limit is not None:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


async def create_message(
    db: AsyncSession,
    *,
    message_in: MessageCreate,
    conversation_id: int,
    sender_type: SenderType,
    gemini_token_usage: Optional[int] = None,
    image_key: Optional[str] = None,
) -> Message:
    """새로운 메시지를 생성합니다."""
    db_message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=message_in.content,
        gemini_token_usage=gemini_token_usage,
        image_key=image_key,
    )
    db.add(db_message)
    await db.flush()
    await db.refresh(db_message)
    return db_message
