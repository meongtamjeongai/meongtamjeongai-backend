# app/api/deps.py
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.security import verify_password
from app.crud import crud_api_key, crud_user
from app.db.session import get_async_db
from app.models.user import User as UserModel
from app.schemas.token import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/password"
)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_principal(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    token_from_header: Optional[str] = Depends(reusable_oauth2),
    api_key_from_header: Optional[str] = Depends(api_key_header),
) -> Tuple[UserModel, List[str]]:
    """
    JWT 또는 API 키를 사용하여 현재 요청의 주체(Principal)를 식별하고,
    (사용자 객체, 보유 스코프 목록) 튜플을 반환합니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    if token_from_header:
        try:
            payload = jwt.decode(
                token_from_header, settings.SECRET_KEY, algorithms=[
                    settings.ALGORITHM]
            )
            token_data = TokenPayload(sub=str(payload.get("sub")))
            user_id = int(token_data.sub)
        except (JWTError, ValidationError, ValueError):
            raise credentials_exception

        user = await crud_user.get_user(db, user_id=user_id)
        if not user:
            raise credentials_exception

        scopes = ["admin:all"] if user.is_superuser else ["user:all"]
        request.state.current_user = user
        request.state.current_scopes = scopes
        return user, scopes

    if api_key_from_header:
        parts = api_key_from_header.split("_")
        if len(parts) != 2:
            raise credentials_exception
        prefix = parts[0]

        db_api_key = await crud_api_key.get_api_key_by_prefix(db, key_prefix=prefix)

        if not db_api_key or not verify_password(api_key_from_header, db_api_key.hashed_key):
            raise credentials_exception

        if db_api_key.expires_at and db_api_key.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="API Key has expired.")

        db_api_key.last_used_at = datetime.now(timezone.utc)
        db.add(db_api_key)
        await db.flush()

        user = db_api_key.user
        if not user:
            raise credentials_exception

        scopes = db_api_key.scopes
        request.state.current_user = user
        request.state.current_scopes = scopes
        return user, scopes

    raise credentials_exception


class HasScope:
    def __init__(self, required_scopes: List[str]):
        self.required_scopes = set(required_scopes)

    def __call__(
        self,
        principal: Tuple[UserModel, List[str]
                         ] = Depends(get_current_principal),
    ) -> None:
        user, current_scopes_list = principal
        current_scopes = set(current_scopes_list)

        if "admin:all" in current_scopes:
            return

        if not self.required_scopes.issubset(current_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required scopes: {', '.join(self.required_scopes)}",
            )


async def get_current_user(
    principal: Tuple[UserModel, List[str]] = Depends(get_current_principal)
) -> UserModel:
    user, _ = principal
    return user


async def get_current_active_user(
    user: UserModel = Depends(get_current_user),
) -> UserModel:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_active_superuser(
    user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    if not user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return user
