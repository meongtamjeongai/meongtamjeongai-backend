# fastapi_backend/app/api/v1/endpoints/auth.py
# 인증 관련 API 엔드포인트 정의

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.crud import crud_user
from app.db.session import get_db
from app.schemas.token import SocialLoginRequest, Token
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/firebase/token",
    response_model=Token,
    summary="Firebase ID 토큰을 사용한 로그인/회원가입",
    description="클라이언트에서 Firebase 인증 후 받은 ID 토큰을 전달하여 서비스 JWT를 발급받습니다.",
    tags=["인증 (Authentication)"],
)
async def login_with_firebase_id_token(
    social_login_request: SocialLoginRequest = Body(...), db: Session = Depends(get_db)
):
    """
    Firebase ID 토큰을 검증하고, 해당 사용자에 대한 서비스 접근 토큰 및 리프레시 토큰을 발급합니다.
    - **id_token**: 클라이언트에서 Firebase SDK를 통해 받은 ID 토큰 문자열.
    """
    auth_service = AuthService(db)

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

    print(f"API: User {user.id} authenticated via Firebase. Returning service tokens.")
    return service_token


@router.post(
    "/token/refresh",
    response_model=Token,  # Access Token만 포함된 Token 스키마 반환
    summary="Access Token 갱신",
    description="유효한 Refresh Token을 사용하여 새로운 Access Token을 발급받습니다.",
    tags=["인증 (Authentication)"],
)
async def refresh_access_token(
    refresh_token: str = Body(
        ..., embed=True, description="클라이언트에 저장된 Refresh Token"
    ),
    db: Session = Depends(get_db),
):
    """
    Refresh Token을 사용하여 만료된 Access Token을 갱신합니다.

    - **refresh_token**: 로그인 시 발급받아 저장해 둔 Refresh Token.
    """
    auth_service = AuthService(db)
    new_access_token = await auth_service.refresh_access_token(
        refresh_token=refresh_token
    )

    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 새로운 Access Token만 반환. Refresh Token은 기존 것 유지.
    return Token(access_token=new_access_token)


# ID/Password 관리자 페이지 로그인 엔드포인트
@router.post(
    "/token",
    response_model=Token,
    summary="이메일/비밀번호 기반 로그인 (관리자용)",
    description="이메일과 비밀번호로 로그인하여 서비스 JWT를 발급받습니다.",
    tags=["인증 (Authentication)"],
)
async def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 호환 폼 데이터(username, password)로 사용자를 인증합니다.
    관리자 앱에서는 username 필드에 이메일을 담아 보냅니다.
    """
    user = crud_user.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # ⭐️ 관리자 로그인 시에는 슈퍼유저인지 확인하는 로직 추가
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have superuser privileges",
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/login/password",
    response_model=Token,
    summary="ID/Password 기반 로그인 (관리자/테스트용)",
    description="이메일과 비밀번호를 사용하여 로그인하고 서비스 JWT를 발급받습니다.",
    tags=["인증 (Authentication)"],
)
async def login_password_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    일반적인 폼 데이터(`username`, `password`)를 받아 사용자를 인증하고 토큰을 발급합니다.
    - **username**: 사용자의 이메일 주소
    - **password**: 사용자의 비밀번호
    """
    auth_service = AuthService(db)
    token = auth_service.authenticate_user_by_password(form_data=form_data)
    return token
