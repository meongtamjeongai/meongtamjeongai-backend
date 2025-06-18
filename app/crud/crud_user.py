# fastapi_backend/app/crud/crud_user.py
# User 모델에 대한 CRUD(Create, Read, Update, Delete) 작업을 위한 함수들

from typing import Any, Dict, Optional, Union, List

from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.models.user_point import UserPoint
from app.schemas.user import UserCreate, UserUpdate

def get_user(db: Session, user_id: int) -> Optional[User]:
    """주어진 ID로 사용자를 조회합니다. (Eager Loading 적용)"""
    return (
        db.query(User)
        .options(selectinload(User.social_accounts), joinedload(User.user_point))
        .filter(User.id == user_id)
        .first()
    )

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """주어진 이메일로 사용자를 조회합니다."""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """여러 사용자를 조회합니다 (페이지네이션)."""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, *, user_in: UserCreate) -> User:
    """새로운 사용자를 생성하고, 기본 UserPoint 레코드도 함께 생성합니다."""
    db_user_data = user_in.model_dump(exclude_unset=True) 
    if user_in.password:
        hashed_password = get_password_hash(user_in.password)
        db_user_data["hashed_password"] = hashed_password
    if "password" in db_user_data:
        del db_user_data["password"]

    db_user = User(**db_user_data)
    db.add(db_user)
    
    # commit을 제거하고, user.id를 얻기 위해 flush를 호출합니다.
    db.flush()
    db.refresh(db_user)

    db_user_point = UserPoint(user_id=db_user.id, points=0) 
    db.add(db_user_point)
    
    return db_user

def update_user(db: Session, *, db_user: User, user_in: Union[UserUpdate, Dict[str, Any]]) -> User:
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
    db.commit()
    db.refresh(db_user)
    return db_user

# --- delete_user 함수를 deactivate_user로 변경 (Soft Delete) ---
def deactivate_user(db: Session, *, user_to_deactivate: User) -> User:
    """
    사용자를 비활성화합니다 (Soft Delete).
    is_active 플래그를 False로 설정합니다.
    """
    user_to_deactivate.is_active = False
    db.add(user_to_deactivate)
    db.commit()
    db.refresh(user_to_deactivate)
    return user_to_deactivate

def authenticate_user(db: Session, *, email: str, password: str) -> Optional[User]:
    """
    이메일과 비밀번호로 사용자를 인증합니다. (일반 로그인 시 사용)
    성공 시 User 객체, 실패 시 None을 반환합니다.
    """
    user = get_user_by_email(db, email=email)
    if not user: return None
    if not user.hashed_password: return None
    if not verify_password(password, user.hashed_password): return None
    return user

def is_active(user: User) -> bool:
    return user.is_active

def is_superuser(user: User) -> bool:
    return user.is_superuser