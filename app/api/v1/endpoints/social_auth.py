# app/api/v1/endpoints/social_auth.py
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_async_db
from app.models.social_account import SocialProvider
from app.schemas.token import Token
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["소셜 로그인 (Social Auth)"])


class SocialTokenRequest(BaseModel):
    access_token: str


async def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
    return AuthService(db)


@router.post("/naver/token", response_model=Token, summary="네이버 소셜 로그인")
async def naver_login(
    token_in: SocialTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://openapi.naver.com/v1/nid/me", headers=headers
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="유효하지 않은 네이버 토큰입니다.")

    user_info = response.json().get("response", {})

    user = await auth_service.get_or_create_social_user(
        provider=SocialProvider.NAVER,
        provider_user_id=user_info.get("id"),
        email=user_info.get("email"),
        username=user_info.get("nickname"),
    )

    if not user:
        raise HTTPException(
            status_code=500, detail="사용자 정보를 처리하는 중 오류가 발생했습니다."
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/kakao/token", response_model=Token, summary="카카오 소셜 로그인")
async def kakao_login(
    token_in: SocialTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    headers = {"Authorization": f"Bearer {token_in.access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://kapi.kakao.com/v2/user/me", headers=headers
        )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="유효하지 않은 카카오 토큰입니다.")

    user_info = response.json()
    kakao_account = user_info.get("kakao_account", {})

    user = await auth_service.get_or_create_social_user(
        provider=SocialProvider.KAKAO,
        provider_user_id=str(user_info.get("id")),
        email=kakao_account.get("email"),
        username=kakao_account.get("profile", {}).get("nickname"),
    )

    if not user:
        raise HTTPException(
            status_code=500, detail="사용자 정보를 처리하는 중 오류가 발생했습니다."
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)
