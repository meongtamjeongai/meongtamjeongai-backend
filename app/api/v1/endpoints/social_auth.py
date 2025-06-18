# app/api/v1/endpoints/social_auth.py

import logging  # 💡 로깅 모듈 임포트

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.crud import crud_social_account, crud_user
from app.db.session import get_db
from app.models.social_account import SocialProvider
from app.schemas.social_account import SocialAccountCreate
from app.schemas.token import Token
from app.schemas.user import UserCreate

# 💡 로거 인스턴스 생성
logger = logging.getLogger(__name__)

router = APIRouter(tags=["소셜 로그인 (Social Auth)"])


class SocialTokenRequest(BaseModel):
    access_token: str


@router.post("/naver/token", response_model=Token, summary="네이버 소셜 로그인")
def naver_login(token_in: SocialTokenRequest, db: Session = Depends(get_db)):
    # 💡 [로그 추가] 네이버 API 호출 시작
    logger.info("Calling Naver API to get user info.")
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)

    if response.status_code != 200:
        # 💡 [로그 추가] 네이버 API 호출 실패 시 상세 정보 기록
        logger.warning(
            f"Failed to get user info from Naver. Status: {response.status_code}, Response: {response.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 네이버 토큰입니다.",
        )

    user_info = response.json().get("response", {})
    naver_id = user_info.get("id")
    email = user_info.get("email")
    nickname = user_info.get("nickname")

    if not naver_id:
        # 💡 [로그 추가] 필수 정보 누락 시
        logger.error(f"Could not get 'id' from Naver user info. Response: {user_info}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="네이버 사용자 정보를 가져오지 못했습니다.",
        )

    # 💡 [로그 추가] 네이버 API 응답 및 핵심 정보 기록
    logger.info(
        f"Successfully got info from Naver. NaverID: {naver_id}, Email: {email}"
    )

    # 💡 [수정] 트랜잭션 관리를 위한 try...except 블록 추가
    try:
        social_account = crud_social_account.get_social_account_by_provider_and_id(
            db, provider=SocialProvider.NAVER, provider_user_id=naver_id
        )

        user = None
        if social_account:
            # 💡 [로그 추가] 기존 사용자 확인
            logger.info(
                f"Found existing user for NaverID: {naver_id}. User ID: {social_account.user_id}"
            )
            user = social_account.user
        else:
            # 💡 [로그 추가] 신규 사용자 생성 흐름 시작
            logger.info(
                f"No social account for NaverID: {naver_id}. Starting new user creation."
            )
            if email:
                logger.info(f"Checking for existing user with email: {email}")
                user = crud_user.get_user_by_email(db, email=email)
                if user:
                    logger.info(
                        f"Found user by email. Linking NaverID {naver_id} to User ID: {user.id}"
                    )

            if not user:
                logger.info("Creating a new user for this Naver account.")

                user_in_data = {
                    "email": email,
                    "username": nickname or f"naver_{naver_id[:8]}",
                    "is_active": True,
                }

                user_in_schema = UserCreate(user_in_data)

                user = crud_user.create_user(db, user_in=user_in_schema)

                logger.info(
                    f"New user created in session. User ID (pre-commit): {user.id}"
                )

            social_account_in = SocialAccountCreate(
                provider=SocialProvider.NAVER, provider_user_id=naver_id
            )
            crud_social_account.create_social_account(
                db, social_account_in=social_account_in, user_id=user.id
            )
            logger.info(
                f"New social account for NaverID {naver_id} created in session."
            )

        # 💡 [수정] 모든 DB 작업이 세션에 추가된 후, 여기서 한번에 커밋
        db.commit()
        logger.info(f"Transaction committed successfully for User ID: {user.id}")

    except Exception as e:
        # 💡 [수정] 중간에 어떤 오류라도 발생하면 모든 작업을 취소(롤백)
        logger.error(
            f"ERROR during Naver login process for NaverID: {naver_id}. Rolling back. Error: {e}",
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the login process: {str(e)}",
        )

    # 💡 [수정] 커밋 후 객체 상태를 최신화하기 위해 refresh
    db.refresh(user)
    # JWT 토큰 생성
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/kakao/token", response_model=Token, summary="카카오 소셜 로그인")
def kakao_login(token_in: SocialTokenRequest, db: Session = Depends(get_db)):
    # 💡 [로그 추가] 카카오 API 호출 시작
    logger.info("Calling Kakao API to get user info.")
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    response = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers)

    if response.status_code != 200:
        # 💡 [로그 추가] 카카오 API 호출 실패 시 상세 정보 기록
        logger.warning(
            f"Failed to get user info from Kakao. Status: {response.status_code}, Response: {response.text}"
        )
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
        # 💡 [로그 추가] 필수 정보 누락 시
        logger.error(f"Could not get 'id' from Kakao user info. Response: {user_info}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="카카오 사용자 정보를 가져오지 못했습니다.",
        )

    # 💡 [로그 추가] 카카오 API 응답 및 핵심 정보 기록
    logger.info(
        f"Successfully got info from Kakao. KakaoID: {kakao_id}, Email: {email}"
    )

    # 💡 [수정] 트랜잭션 관리를 위한 try...except 블록 추가
    try:
        social_account = crud_social_account.get_social_account_by_provider_and_id(
            db, provider=SocialProvider.KAKAO, provider_user_id=kakao_id
        )

        user = None
        if social_account:
            # 💡 [로그 추가] 기존 사용자 확인
            logger.info(
                f"Found existing user for KakaoID: {kakao_id}. User ID: {social_account.user_id}"
            )
            user = social_account.user
        else:
            # 💡 [로그 추가] 신규 사용자 생성 흐름 시작
            logger.info(
                f"No social account for KakaoID: {kakao_id}. Starting new user creation."
            )
            if email:
                logger.info(f"Checking for existing user with email: {email}")
                user = crud_user.get_user_by_email(db, email=email)
                if user:
                    logger.info(
                        f"Found user by email. Linking KakaoID {kakao_id} to User ID: {user.id}"
                    )

            if not user:
                logger.info("Creating a new user for this Kakao account.")

                user_in_data = {
                    "email": email,
                    "username": nickname or f"kakao_{kakao_id[:8]}",
                    "is_active": True,
                }
                user_in_schema = UserCreate(user_in_data)

                user = crud_user.create_user(db, user_in=user_in_schema)

                logger.info(
                    f"New user created in session. User ID (pre-commit): {user.id}"
                )

            social_account_in = SocialAccountCreate(
                provider=SocialProvider.KAKAO, provider_user_id=kakao_id
            )
            crud_social_account.create_social_account(
                db, social_account_in=social_account_in, user_id=user.id
            )
            logger.info(
                f"New social account for KakaoID {kakao_id} created in session."
            )

        # 💡 [수정] 모든 DB 작업이 세션에 추가된 후, 여기서 한번에 커밋
        db.commit()
        logger.info(f"Transaction committed successfully for User ID: {user.id}")

    except Exception as e:
        # 💡 [수정] 중간에 어떤 오류라도 발생하면 모든 작업을 취소(롤백)
        logger.error(
            f"ERROR during Kakao login process for KakaoID: {kakao_id}. Rolling back. Error: {e}",
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the login process: {str(e)}",
        )

    # 💡 [수정] 커밋 후 객체 상태를 최신화하기 위해 refresh
    db.refresh(user)
    # JWT 토큰 생성
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)
