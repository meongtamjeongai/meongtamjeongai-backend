# app/crud/crud_user.py
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query, joinedload, selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.models.user_point import UserPoint
from app.schemas.user import UserCreate, UserUpdate

# ✅ User 모델을 위한 공통 로딩 옵션 변수 정의
_USER_EAGER_LOADING_OPTIONS = (
    selectinload(User.social_accounts),
    joinedload(User.user_point),
)


# ✅ User 모델을 위한 기본 쿼리 헬퍼 함수 정의
def _get_base_user_query() -> Query:
    """User 모델에 대한 기본 SELECT 쿼리 및 공통 로딩 옵션을 반환합니다."""
    return select(User).options(*_USER_EAGER_LOADING_OPTIONS)


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """주어진 ID로 사용자를 조회합니다. (Eager Loading 적용)"""
    stmt = _get_base_user_query().where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """주어진 이메일로 사용자를 조회합니다."""
    stmt = _get_base_user_query().where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """여러 사용자를 조회합니다 (페이지네이션)."""
    stmt = _get_base_user_query().offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_user(db: AsyncSession, *, user_in: UserCreate) -> User:
    """새로운 사용자를 생성하고, 기본 UserPoint 레코드도 함께 생성합니다."""
    db_user_data = user_in.model_dump(exclude_unset=True)
    if user_in.password:
        hashed_password = get_password_hash(user_in.password)
        db_user_data["hashed_password"] = hashed_password
    if "password" in db_user_data:
        del db_user_data["password"]

    db_user = User(**db_user_data)
    db.add(db_user)
    await db.flush()

    db_user_point = UserPoint(user_id=db_user.id, points=0)
    db.add(db_user_point)
    await db.flush()

    await db.refresh(db_user)
    # 🔄 생성 후 완전한 객체를 반환하기 위해 다시 조회하는 로직 추가
    return await get_user(db, user_id=db_user.id)


async def update_user(
    db: AsyncSession, *, db_user: User, user_in: Union[UserUpdate, Dict[str, Any]]
) -> User:
    """기존 사용자의 정보를 업데이트합니다."""
    if isinstance(user_in, dict):
        update_data = user_in
    else:
        update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]

    for field, value in update_data.items():
        if hasattr(db_user, field):
            setattr(db_user, field, value)

    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def deactivate_user(db: AsyncSession, *, user_to_deactivate: User) -> User:
    """사용자를 비활성화합니다 (Soft Delete)."""
    user_to_deactivate.is_active = False
    db.add(user_to_deactivate)
    await db.flush()
    await db.refresh(user_to_deactivate)
    return user_to_deactivate


async def authenticate_user(
    db: AsyncSession, *, email: str, password: str
) -> Optional[User]:
    """이메일과 비밀번호로 사용자를 인증합니다."""
    user = await get_user_by_email(db, email=email)
    if not user:
        return None
    if not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def is_active(user: User) -> bool:
    return user.is_active


def is_superuser(user: User) -> bool:
    return user.is_superuser
