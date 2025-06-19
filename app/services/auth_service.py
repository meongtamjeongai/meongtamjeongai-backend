# app/services/auth_service.py
import logging
from typing import Any, Dict, Optional, Tuple

import firebase_admin
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth as firebase_auth
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    ALGORITHM,
    JWT_REFRESH_SECRET_KEY,
    create_access_token,
    create_refresh_token,
)
from app.crud import crud_social_account, crud_user
from app.models.social_account import SocialProvider
from app.models.user import User
from app.schemas.social_account import SocialAccountCreate
from app.schemas.token import Token, TokenPayload
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_firebase_id_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Firebase ID 토큰을 검증하고 디코딩된 토큰 정보를 반환합니다."""
        if not firebase_admin._apps:
            logger.error("AuthService Error: Firebase Admin SDK not initialized.")
            return None
        try:
            decoded_token = firebase_auth.verify_id_token(
                token, check_revoked=False, clock_skew_seconds=10
            )
            return decoded_token
        except firebase_auth.InvalidIdTokenError as e:
            logger.warning(f"AuthService: Invalid Firebase ID token: {e}")
            return None
        except Exception as e:
            logger.error(
                f"AuthService: Unexpected error verifying Firebase ID token: {e}",
                exc_info=True,
            )
            return None

    async def get_or_create_user_from_firebase_token(
        self,
        decoded_token: Dict[str, Any],
    ) -> Optional[User]:
        """디코딩된 Firebase 토큰 정보를 기반으로 사용자를 조회하거나 생성합니다."""
        firebase_uid = decoded_token.get("uid")
        if not firebase_uid:
            return None

        email = decoded_token.get("email")
        firebase_provider_id = decoded_token.get("firebase", {}).get("sign_in_provider")

        provider: Optional[SocialProvider] = None
        if firebase_provider_id == "google.com":
            provider = SocialProvider.FIREBASE_GOOGLE
        elif firebase_provider_id == "anonymous":
            provider = SocialProvider.FIREBASE_ANONYMOUS
        else:
            logger.warning(
                f"AuthService: Unsupported Firebase sign_in_provider: {firebase_provider_id}"
            )
            return None

        # Firebase 토큰 기반 사용자는 이 메소드에서 직접 처리
        social_account = (
            await crud_social_account.get_social_account_by_provider_and_id(
                self.db, provider=provider, provider_user_id=firebase_uid
            )
        )

        if social_account:
            return social_account.user
        else:
            existing_user_by_email = None
            if email:
                existing_user_by_email = await crud_user.get_user_by_email(
                    self.db, email=email
                )

            if existing_user_by_email:
                user_to_link = existing_user_by_email
            else:
                user_create_data = {
                    "email": email,
                    "username": decoded_token.get("name")
                    or f"guest_{firebase_uid[:8]}",
                    "is_active": True,
                    "is_guest": provider == SocialProvider.FIREBASE_ANONYMOUS,
                }
                user_in = UserCreate(**user_create_data)
                user_to_link = await crud_user.create_user(self.db, user_in=user_in)

            social_account_in = SocialAccountCreate(
                provider=provider, provider_user_id=firebase_uid
            )
            await crud_social_account.create_social_account(
                self.db, social_account_in=social_account_in, user_id=user_to_link.id
            )
            return user_to_link

    async def get_or_create_social_user(
        self,
        *,
        provider: SocialProvider,
        provider_user_id: str,
        email: Optional[str],
        username: Optional[str],
    ) -> User:
        """
        소셜 로그인 정보를 받아 사용자를 조회하거나 생성합니다.
        하나의 트랜잭션으로 관리됩니다.
        """
        if not provider_user_id:
            raise HTTPException(status_code=400, detail="Provider user ID is required.")

        social_account = (
            await crud_social_account.get_social_account_by_provider_and_id(
                self.db, provider=provider, provider_user_id=provider_user_id
            )
        )
        if social_account:
            return social_account.user

        user = None
        if email:
            user = await crud_user.get_user_by_email(self.db, email=email)

        if not user:
            user_in = UserCreate(
                email=email,
                username=username or f"{provider.value}_{provider_user_id[:8]}",
                is_active=True,
            )
            user = await crud_user.create_user(self.db, user_in=user_in)

        social_account_in = SocialAccountCreate(
            provider=provider, provider_user_id=provider_user_id
        )
        await crud_social_account.create_social_account(
            self.db, social_account_in=social_account_in, user_id=user.id
        )

        return user

    async def authenticate_with_firebase_id_token(
        self, id_token: str
    ) -> Optional[Tuple[User, Token]]:
        decoded_token = await self.verify_firebase_id_token(id_token)
        if not decoded_token:
            return None

        user = await self.get_or_create_user_from_firebase_token(decoded_token)
        if not user or not user.is_active:
            return None

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        service_token = Token(access_token=access_token, refresh_token=refresh_token)
        return user, service_token

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        try:
            payload = jwt.decode(
                refresh_token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
            )
            if payload.get("type") != "refresh":
                return None
            token_data = TokenPayload(**payload)
            user_id = int(token_data.sub)
            user = await crud_user.get_user(self.db, user_id=user_id)
            if not user or not user.is_active:
                return None
            new_access_token = create_access_token(subject=user.id)
            return new_access_token
        except (JWTError, ValueError, TypeError):
            return None

    async def authenticate_user_by_password(
        self, form_data: OAuth2PasswordRequestForm
    ) -> tuple[User, Token]:
        user = await crud_user.authenticate_user(
            self.db, email=form_data.username, password=form_data.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        token = Token(access_token=access_token, refresh_token=refresh_token)
        return user, token
