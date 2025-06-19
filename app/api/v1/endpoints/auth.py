# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.schemas.token import SocialLoginRequest, Token
from app.services.auth_service import AuthService

router = APIRouter()


async def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/firebase/token",
    response_model=Token,
    summary="Firebase ID 토큰을 사용한 로그인/회원가입",
    tags=["인증 (Authentication)"],
)
async def login_with_firebase_id_token(
    social_login_request: SocialLoginRequest = Body(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    result = await auth_service.authenticate_with_firebase_id_token(
        id_token=social_login_request.token
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token or failed to authenticate user.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user, service_token = result
    return service_token


@router.post(
    "/token/refresh",
    response_model=Token,
    summary="Access Token 갱신",
    tags=["인증 (Authentication)"],
)
async def refresh_access_token(
    refresh_token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
):
    new_access_token = await auth_service.refresh_access_token(
        refresh_token=refresh_token
    )
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=new_access_token)


@router.post(
    "/token",
    response_model=Token,
    summary="[관리자 앱 전용] 이메일/비밀번호 로그인",
    tags=["인증 (Authentication)"],
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    user, token = await auth_service.authenticate_user_by_password(form_data=form_data)

    # 슈퍼유저인지 확인하는 로직
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have superuser privileges",
        )
    return token


@router.post(
    "/login/password",
    response_model=Token,
    summary="[API 문서 테스트용] ID/Password 로그인",
    tags=["인증 (Authentication)"],
)
async def login_password_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    user, token = await auth_service.authenticate_user_by_password(form_data=form_data)
    return token
