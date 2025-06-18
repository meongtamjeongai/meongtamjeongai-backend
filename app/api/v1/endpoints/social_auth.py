# app/api/v1/endpoints/social_auth.py

import requests
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.crud import crud_social_account, crud_user
from app.db.session import get_db
from app.models.social_account import SocialProvider
from app.schemas.social_account import SocialAccountCreate
from app.schemas.token import Token

router = APIRouter(tags=["소셜 로그인 (Social Auth)"])

logger = logging.getLogger(__name__) # 로거 인스턴스 생성

class SocialTokenRequest(BaseModel):
    access_token: str

@router.post("/naver/token", response_model=Token, summary="네이버 소셜 로그인")
def naver_login(token_in: SocialTokenRequest, db: Session = Depends(get_db)):
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 네이버 토큰입니다.",
        )

    user_info = response.json().get("response", {})
    naver_id = user_info.get("id")
    email = user_info.get("email")
    nickname = user_info.get("nickname")

    if not naver_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="네이버 사용자 정보를 가져오지 못했습니다.",
        )

    try:
        # DB에서 소셜 계정 조회
        social_account = crud_social_account.get_social_account_by_provider_and_id(
            db, provider=SocialProvider.NAVER, provider_user_id=naver_id
        )

        if social_account:
            user = social_account.user
        else:
            # 이메일 기준 기존 유저 조회
            user = crud_user.get_user_by_email(db, email=email)
            if not user:
                user_in = {
                    "email": email,
                    "username": nickname or f"naver_{naver_id[:8]}",
                    "is_active": True,
                }
                
                user = crud_user.create_user(db, user_in=user_in)

            # 소셜 계정 생성
            social_account_in = SocialAccountCreate(
                provider=SocialProvider.NAVER, provider_user_id=naver_id
            )
            crud_social_account.create_social_account(
                db, social_account_in=social_account_in, user_id=user.id
            )

            db.commit()

    except Exception as e:
        # 💡 오류 발생 시 롤백
        db.rollback()
        # 에러 로깅은 전역 예외 핸들러에서 처리될 것이므로, 여기서는 예외를 다시 발생시키거나
        # 구체적인 HTTPException을 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the login process: {str(e)}"
        )

    db.refresh(user)

    # JWT 토큰 생성
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/kakao/token", response_model=Token, summary="카카오 소셜 로그인")
def kakao_login(token_in: SocialTokenRequest, db: Session = Depends(get_db)):
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    response = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 카카오 토큰입니다.",
        )

    user_info = response.json()
    kakao_id = str(user_info.get("id"))
    kakao_account = user_info.get("kakao_account", {})
    email = kakao_account.get("email")
    profile = kakao_account.get("profile", {})
    nickname = profile.get("nickname")

    if not kakao_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="카카오 사용자 정보를 가져오지 못했습니다.",
        )

    logger.info(
        f"Successfully got info from Kakao. KakaoID: {kakao_id}, Email: {email}"
    )

    try:
        social_account = crud_social_account.get_social_account_by_provider_and_id(
            db, provider=SocialProvider.KAKAO, provider_user_id=kakao_id
        )

        if social_account:
            logger.info(f"Found existing user for KakaoID: {kakao_id}. User ID: {social_account.user_id}")
            user = social_account.user
        else:
            logger.info(f"No social account for KakaoID: {kakao_id}. Starting new user creation.")
            user = None
            if email:
                logger.info(f"Checking for existing user with email: {email}")
                user = crud_user.get_user_by_email(db, email=email)
                if user:
                    logger.info(f"Found user by email. Linking KakaoID {kakao_id} to User ID: {user.id}")

            if not user:
                logger.info("Creating a new user for this Kakao account.")
                user_in = {
                    "email": email,
                    "username": nickname or f"kakao_{kakao_id[:8]}",
                    "is_active": True,
                }
                user = crud_user.create_user(db, user_in=user_in)
                logger.info(f"New user created in session. User ID (pre-commit): {user.id}")

            social_account_in = SocialAccountCreate(...)
            crud_social_account.create_social_account(db, social_account_in=social_account_in, user_id=user.id)
            logger.info(f"New social account for KakaoID {kakao_id} created in session.")

        db.commit()
        logger.info(f"Transaction committed successfully for User ID: {user.id}")

    except Exception as e:
        # 💡 오류 발생 시 롤백
        db.rollback()
        # 에러 로깅은 전역 예외 핸들러에서 처리될 것이므로, 여기서는 예외를 다시 발생시키거나
        # 구체적인 HTTPException을 발생시킵니다.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the login process: {str(e)}"
        )        

    db.refresh(user)

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)
