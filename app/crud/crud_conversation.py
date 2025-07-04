# app/crud/crud_conversation.py
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query, joinedload, selectinload

from app.models.conversation import Conversation
from app.models.phishing_case import PhishingCase
from app.schemas.conversation import ConversationCreate
from app.models.user import User

_CONVERSATION_EAGER_LOADING_OPTIONS = (
    # Conversation.user를 로드할 때, User의 하위 관계까지 즉시 로딩하도록 연쇄적으로 설정합니다.
    joinedload(Conversation.user).options(
        selectinload(User.social_accounts), 
        joinedload(User.user_point)
    ),
    selectinload(Conversation.persona),
    selectinload(Conversation.applied_phishing_case).joinedload(PhishingCase.category),
)


# ✅ 2. 기본 쿼리 객체를 생성하는 내부 헬퍼 함수를 만듭니다.
def _get_base_conversation_query() -> Query:
    """
    Conversation 모델에 대한 기본 SELECT 쿼리를 생성하고,
    공통 Eager Loading 옵션을 적용하여 반환합니다.
    """
    return select(Conversation).options(*_CONVERSATION_EAGER_LOADING_OPTIONS)


# ✅ 3. 기존 CRUD 함수들을 리팩토링하여 헬퍼 함수를 사용하도록 변경합니다.


async def get_conversation(
    db: AsyncSession, conversation_id: int, user_id: Optional[int] = None
) -> Optional[Conversation]:
    """주어진 ID로 대화방을 조회합니다."""
    # 헬퍼 함수로 기본 쿼리 생성 후, 특정 조건(where) 추가
    stmt = _get_base_conversation_query().where(Conversation.id == conversation_id)
    if user_id:
        stmt = stmt.where(Conversation.user_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_conversations_by_user(
    db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """특정 사용자의 모든 대화방 목록을 최신 메시지 시간 순으로 정렬하여 조회합니다."""
    # 헬퍼 함수로 기본 쿼리 생성 후, 조건 및 정렬/페이징 추가
    stmt = (
        _get_base_conversation_query()
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.last_message_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_all_conversations(
    db: AsyncSession, *, skip: int = 0, limit: int = 100
) -> List[Conversation]:
    """모든 대화방 목록을 조회합니다. (관리자용)"""
    # 헬퍼 함수로 기본 쿼리 생성 후, 정렬/페이징 추가
    stmt = (
        _get_base_conversation_query()
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

    # 생성 후, Eager Loading이 적용된 완전한 객체를 반환하기 위해 get_conversation 호출
    return await get_conversation(db, conversation_id=db_conversation.id)

async def update_conversation(
    db: AsyncSession, *, db_conv: Conversation
) -> Conversation:
    """
    대화방 객체의 변경사항을 DB에 반영하고, 관계가 로드된 완전한 객체를 반환합니다.
    """
    db.add(db_conv)
    await db.flush()
    # await db.refresh(db_conv) # 더 이상 필요 없으므로 삭제하거나 주석 처리합니다.

    # get_conversation 함수를 사용하여 Eager Loading이 적용된 객체를 다시 조회하여 반환합니다.
    updated_conversation = await get_conversation(db, conversation_id=db_conv.id)
    if not updated_conversation:
        # 이 경우는 거의 발생하지 않지만, 방어적으로 처리합니다.
        raise RuntimeError(f"Failed to re-fetch conversation with id {db_conv.id} after update.")

    return updated_conversation

async def delete_conversation(db: AsyncSession, *, conversation_id: int) -> Optional[Conversation]:
    """주어진 ID의 대화방을 삭제합니다."""
    db_conv = await get_conversation(db, conversation_id=conversation_id)
    if db_conv:
        await db.delete(db_conv)
        await db.flush()
    return db_conv