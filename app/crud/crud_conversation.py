# app/crud/crud_conversation.py
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationCreateAdmin


async def get_conversation(
    db: AsyncSession, conversation_id: int, user_id: Optional[int] = None
) -> Optional[Conversation]:
    """주어진 ID로 대화방을 조회합니다."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_conversations_by_user(
    db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """특정 사용자의 모든 대화방 목록을 최신 메시지 시간 순으로 정렬하여 조회합니다."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .options(joinedload(Conversation.persona))
        .order_by(desc(Conversation.last_message_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_conversation(
    db: AsyncSession, *, conversation_in: ConversationCreate, user_id: int
) -> Conversation:
    """새로운 대화방을 생성합니다."""
    db_conversation_data = conversation_in.model_dump(exclude_unset=True)
    db_conversation = Conversation(**db_conversation_data, user_id=user_id)
    db.add(db_conversation)
    await db.flush()
    await db.refresh(db_conversation)
    return db_conversation


async def update_conversation(db: AsyncSession, *, db_conv: Conversation) -> Conversation:
    """대화방 객체의 변경사항을 DB에 반영합니다."""
    db.add(db_conv)
    await db.flush()
    await db.refresh(db_conv)
    return db_conv


async def delete_conversation(db: AsyncSession, *, conversation_id: int) -> Optional[Conversation]:
    """주어진 ID의 대화방을 삭제합니다."""
    db_conversation = await get_conversation(db, conversation_id=conversation_id)
    if db_conversation:
        # SQLAlchemy 2.0.16 이상에서는 delete가 비동기 함수
        await db.delete(db_conversation)
        await db.flush()
    return db_conversation


async def get_all_conversations(
    db: AsyncSession, *, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """모든 대화방 목록을 조회합니다. (관리자용)"""
    stmt = (
        select(Conversation)
        .options(
            joinedload(Conversation.persona),
            joinedload(Conversation.user),
            joinedload(Conversation.applied_phishing_case),
        )
        .order_by(desc(Conversation.last_message_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def delete_conversation_by_id(
    db: AsyncSession, *, conversation_id: int
) -> Optional[Conversation]:
    """ID로 대화방을 삭제합니다. (관리자용)"""
    db_conversation = await get_conversation(db, conversation_id=conversation_id)
    if db_conversation:
        await db.delete(db_conversation)
        await db.flush()
    return db_conversation
