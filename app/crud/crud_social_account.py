# app/crud/crud_social_account.py
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount, SocialProvider
from app.schemas.social_account import SocialAccountCreate


async def get_social_account(db: AsyncSession, social_account_id: int) -> Optional[SocialAccount]:
    """주어진 ID로 소셜 계정을 조회합니다."""
    stmt = select(SocialAccount).where(SocialAccount.id == social_account_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_social_account_by_provider_and_id(
    db: AsyncSession, *, provider: SocialProvider, provider_user_id: str
) -> Optional[SocialAccount]:
    """특정 제공자와 해당 제공자의 사용자 ID로 소셜 계정을 조회합니다."""
    stmt = select(SocialAccount).where(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == provider_user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_social_accounts_by_user_id(db: AsyncSession, user_id: int) -> List[SocialAccount]:
    """특정 사용자의 모든 소셜 계정을 조회합니다."""
    stmt = select(SocialAccount).where(SocialAccount.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_social_account(
    db: AsyncSession, *, social_account_in: SocialAccountCreate, user_id: int
) -> SocialAccount:
    """새로운 소셜 계정을 생성하고 사용자와 연결합니다."""
    db_social_account = SocialAccount(
        **social_account_in.model_dump(),
        user_id=user_id,
    )
    db.add(db_social_account)
    await db.flush()
    await db.refresh(db_social_account)
    return db_social_account


async def delete_social_account(db: AsyncSession, *, social_account_id: int) -> Optional[SocialAccount]:
    """주어진 ID의 소셜 계정을 삭제합니다."""
    db_social_account = await get_social_account(db, social_account_id=social_account_id)
    if db_social_account:
        await db.delete(db_social_account)
        await db.flush()
    return db_social_account
