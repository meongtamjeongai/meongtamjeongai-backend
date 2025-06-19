# app/services/api_key_service.py
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.crud import crud_api_key
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate


class ApiKeyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self, *, api_key_in: ApiKeyCreate, current_user: User
    ) -> tuple[ApiKey, str]:
        """
        새로운 API 키를 생성하고 DB에 저장합니다.
        Race Condition을 방지하기 위해 DB의 UNIQUE 제약조건을 활용한 재시도 로직을 포함합니다.
        """
        created_api_key = None
        plain_api_key = ""

        for _ in range(settings.API_KEY_MAX_RETRIES):
            prefix = secrets.token_urlsafe(settings.API_KEY_PREFIX_LENGTH)
            secret = secrets.token_urlsafe(settings.API_KEY_SECRET_LENGTH)
            plain_api_key = f"{prefix}_{secret}"

            expires_at = None
            if api_key_in.expires_in_days:
                expires_at = datetime.now(
                    timezone.utc) + timedelta(days=api_key_in.expires_in_days)

            db_obj = ApiKey(
                key_prefix=prefix,
                hashed_key=get_password_hash(plain_api_key),
                user_id=current_user.id,
                description=api_key_in.description,
                scopes=[scope.value for scope in api_key_in.scopes],
                expires_at=expires_at,
            )

            try:
                created_api_key = await crud_api_key.create_api_key(self.db, db_obj=db_obj)
                break
            except IntegrityError:
                await self.db.rollback()

        if not created_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate a unique API key.",
            )

        return created_api_key, plain_api_key

    async def revoke_api_key(self, *, api_key_id: int, current_user: User) -> ApiKey:
        """
        API 키를 폐기(비활성화)합니다.
        본인이 발급한 키 또는 슈퍼유저만 폐기할 수 있습니다.
        """
        key_to_deactivate = await crud_api_key.get_api_key(self.db, api_key_id=api_key_id)

        if not key_to_deactivate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found"
            )

        if not current_user.is_superuser and key_to_deactivate.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to deactivate this API Key",
            )

        return await crud_api_key.deactivate_api_key(self.db, db_obj=key_to_deactivate)
