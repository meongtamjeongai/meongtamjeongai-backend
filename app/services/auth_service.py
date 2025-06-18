# fastapi_backend/app/services/auth_service.py

import logging
from typing import Any, Dict, Optional, Tuple

import firebase_admin
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from firebase_admin import auth as firebase_auth
from jose import JWTError, jwt
from sqlalchemy.orm import Session

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

# 로거 설정
logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    async def verify_firebase_id_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Firebase ID 토큰을 검증하고 디코딩된 토큰 정보(dict)를 반환합니다.
        유효하지 않으면 None을 반환합니다.
        """
        if not firebase_admin._apps:
            logger.error("AuthService Error: Firebase Admin SDK not initialized.")
            return None
        try:
            # 💡 [해결책] clock_skew_seconds 옵션을 추가하여 최대 10초의 시간 오차를 허용합니다.
            decoded_token = firebase_auth.verify_id_token(
                token, check_revoked=False, clock_skew_seconds=10
            )
            return decoded_token
        except firebase_auth.InvalidIdTokenError as e:
            # 토큰이 유효하지 않은 경우 (만료, 서명 불일치, 시간 문제 등)
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
        """
        디코딩된 Firebase 토큰 정보를 기반으로 사용자를 조회하거나 생성합니다.
        """
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

        social_account = crud_social_account.get_social_account_by_provider_and_id(
            self.db, provider=provider, provider_user_id=firebase_uid
        )

        if social_account:
            logger.info(
                f"AuthService: Found existing social account for firebase_uid: {firebase_uid}, provider: {provider.value}"
            )
            return social_account.user
        else:
            logger.info(
                f"AuthService: No existing social account found for firebase_uid: {firebase_uid}. Creating new user."
            )

            try:
                existing_user_by_email = None
                if email:
                    existing_user_by_email = crud_user.get_user_by_email(
                        self.db, email=email
                    )

                if existing_user_by_email:
                    user_to_link = existing_user_by_email
                    logger.info(
                        f"AuthService: Linking new social account to existing user with email: {email}"
                    )
                else:
                    user_create_data = {
                        "email": email,
                        "username": decoded_token.get("name")
                        if provider == SocialProvider.FIREBASE_GOOGLE
                        else f"guest_{firebase_uid[:8]}",
                        "is_active": True,
                        "is_guest": provider == SocialProvider.FIREBASE_ANONYMOUS,
                    }
                    user_in = UserCreate(**user_create_data)
                    user_to_link = crud_user.create_user(self.db, user_in=user_in)
                    logger.info(
                        f"AuthService: Created new user. UID: {user_to_link.id}, Email: {user_to_link.email}"
                    )

                social_account_in = SocialAccountCreate(
                    provider=provider, provider_user_id=firebase_uid
                )
                crud_social_account.create_social_account(
                    self.db, social_account_in=social_account_in, user_id=user_to_link.id
                )
                self.db.commit()
                logger.info(
                    f"AuthService: Created new social account for user_id: {user_to_link.id}"
                )
                self.db.refresh(user_to_link)
                return user_to_link
            except Exception as e:
                # 💡 오류 발생 시 롤백하여 데이터 불일치를 방지합니다.
                logger.error(f"Error during user/social account creation: {e}", exc_info=True)
                self.db.rollback()
                # None을 반환하거나, 혹은 여기서 바로 HTTPException을 발생시킬 수도 있습니다.
                return None

    async def authenticate_with_firebase_id_token(
        self, id_token: str
    ) -> Optional[Tuple[User, Token]]:
        decoded_token = await self.verify_firebase_id_token(id_token)
        if not decoded_token:
            return None

        user = await self.get_or_create_user_from_firebase_token(decoded_token)
        if not user:
            return None

        if not user.is_active:
            logger.warning(f"AuthService: User {user.id} is inactive.")
            return None

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        service_token = Token(access_token=access_token, refresh_token=refresh_token)

        logger.info(
            f"AuthService: User {user.id} authenticated successfully. Tokens generated."
        )
        return user, service_token

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        try:
            payload = jwt.decode(
                refresh_token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
            )
            logger.info(
                f"AuthService (refresh_access_token): Refresh token decoded. Payload: {payload}"
            )

            if payload.get("type") != "refresh":
                logger.warning(
                    "AuthService (refresh_access_token): Invalid token type, expected 'refresh'."
                )
                return None

            token_data = TokenPayload(**payload)
            user_id = int(token_data.sub)

            user = crud_user.get_user(self.db, user_id=user_id)
            if not user or not user.is_active:
                logger.warning(
                    f"AuthService (refresh_access_token): User {user_id} not found or inactive."
                )
                return None

            new_access_token = create_access_token(subject=user.id)
            logger.info(
                f"AuthService (refresh_access_token): New access token generated for user {user.id}."
            )
            return new_access_token

        except JWTError as e:
            logger.warning(
                f"AuthService (refresh_access_token): Invalid refresh token: {e}"
            )
            return None
        except (ValueError, TypeError):
            logger.warning(
                "AuthService (refresh_access_token): Invalid payload in refresh token."
            )
            return None

    # ID/Password 기반 인증 서비스 메소드 추가
    def authenticate_user_by_password(
        self, form_data: OAuth2PasswordRequestForm
    ) -> Token:
        """
        사용자명(이메일)과 비밀번호로 사용자를 인증하고 JWT 토큰을 반환합니다.
        """
        # crud_user의 authenticate_user 함수를 사용하여 DB에서 사용자 검증
        user = crud_user.authenticate_user(
            self.db, email=form_data.username, password=form_data.password
        )

        # 사용자가 없거나 비밀번호가 틀린 경우
        if not user:
            logger.warning(
                f"AuthService: Password authentication failed for email: {form_data.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 비활성화된 사용자인 경우
        if not user.is_active:
            logger.warning(
                f"AuthService: Inactive user tried to log in: {form_data.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        # 인증 성공 시, Access Token과 Refresh Token 생성
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        logger.info(
            f"AuthService: User {user.id} ({user.email}) authenticated via password. Tokens generated."
        )
        return Token(access_token=access_token, refresh_token=refresh_token)
