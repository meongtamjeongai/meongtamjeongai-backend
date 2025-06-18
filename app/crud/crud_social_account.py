# fastapi_backend/app/crud/crud_social_account.py
# SocialAccount 모델에 대한 CRUD 작업을 위한 함수들

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.social_account import (  # 모델 및 Enum 임포트
    SocialAccount,
    SocialProvider,
)
from app.schemas.social_account import SocialAccountCreate  # 스키마 임포트

# --- SocialAccount CRUD 함수들 ---


def get_social_account(db: Session, social_account_id: int) -> Optional[SocialAccount]:
    """주어진 ID로 소셜 계정을 조회합니다."""
    return db.query(SocialAccount).filter(SocialAccount.id == social_account_id).first()


def get_social_account_by_provider_and_id(
    db: Session, *, provider: SocialProvider, provider_user_id: str
) -> Optional[SocialAccount]:
    """특정 제공자와 해당 제공자의 사용자 ID로 소셜 계정을 조회합니다."""
    return (
        db.query(SocialAccount)
        .filter(
            SocialAccount.provider == provider,
            SocialAccount.provider_user_id == provider_user_id,
        )
        .first()
    )


def get_social_accounts_by_user_id(db: Session, user_id: int) -> List[SocialAccount]:
    """특정 사용자의 모든 소셜 계정을 조회합니다."""
    return db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()

def create_social_account(
    db: Session, *, social_account_in: SocialAccountCreate, user_id: int
) -> SocialAccount:
    """새로운 소셜 계정을 생성하고 사용자와 연결합니다."""
    db_social_account = SocialAccount(
        **social_account_in.model_dump(),
        user_id=user_id,
    )
    db.add(db_social_account)
    # 💡 [수정] commit과 refresh를 제거합니다.
    return db_social_account

def delete_social_account(
    db: Session, *, social_account_id: int
) -> Optional[SocialAccount]:
    """주어진 ID의 소셜 계정을 삭제합니다."""
    db_social_account = (
        db.query(SocialAccount).filter(SocialAccount.id == social_account_id).first()
    )
    if db_social_account:
        db.delete(db_social_account)
        db.commit()
        return db_social_account
    return None


# (Update는 일반적으로 provider_user_id 등을 변경하지 않으므로, 필요성은 낮음)
