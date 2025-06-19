# app/crud/crud_api_key.py
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


async def create_api_key(db: AsyncSession, *, db_obj: ApiKey) -> ApiKey:
    """
    미리 생성된 ApiKey 모델 객체를 받아 DB에 저장합니다.
    """
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def get_api_key_by_prefix(db: AsyncSession, *, key_prefix: str) -> Optional[ApiKey]:
    """
    API 키 접두사로 '활성화된' 키 정보를 조회합니다.
    """
    stmt = select(ApiKey).where(
        ApiKey.key_prefix == key_prefix, ApiKey.is_active == True
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_api_keys_by_user(
    db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
) -> List[ApiKey]:
    """
    특정 사용자가 발급한 모든 API 키 목록을 조회합니다.
    """
    stmt = (
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_api_key(db: AsyncSession, *, api_key_id: int) -> Optional[ApiKey]:
    """
    ID로 특정 API 키를 조회합니다. (활성 여부와 무관하게 조회)
    """
    stmt = select(ApiKey).where(ApiKey.id == api_key_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def deactivate_api_key(db: AsyncSession, *, db_obj: ApiKey) -> ApiKey:
    """
    API 키를 비활성화(Soft Delete)합니다.
    """
    db_obj.is_active = False
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj
