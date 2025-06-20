# fastapi_backend/app/api/v1/endpoints/users.py
# 사용자 정보 관련 API 엔드포인트 정의

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session  # Session 임포트 추가

from app.api.deps import get_current_active_user
from app.db.session import get_async_db  # get_async_db 임포트 추가
from app.models.user import User as UserModel
from app.schemas.user import (  # UserUpdate 임포트 추가
    UserClientProfileResponse,
    UserUpdate,
)
from app.services.user_service import UserService  # UserService 임포트

router = APIRouter()


async def get_user_service(db: Session = Depends(get_async_db)) -> UserService:
    return UserService(db)


@router.get(
    "/me",
    response_model=UserClientProfileResponse,
    summary="현재 로그인된 사용자 프로필 조회",
    tags=["사용자 (Users)"],
)
async def read_current_user_me(
    current_user: UserModel = Depends(get_current_active_user),
):
    return current_user


# --- 새로운 엔드포인트 추가: PUT /me ---


@router.put(
    "/me",
    response_model=UserClientProfileResponse,
    summary="사용자 정보 수정",
    description="현재 로그인된 사용자의 정보를 수정합니다 (예: 사용자 이름).",
    tags=["사용자 (Users)"],
)
async def update_current_user_info(
    user_in: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    사용자 정보를 업데이트합니다.
    - **Request Body**: `UserUpdate` 스키마에 맞는 수정할 필드.
      (예: `{"username": "새로운이름"}`)
    """
    updated_user = await user_service.update_user_info(
        current_user=current_user, user_in=user_in
    )
    return updated_user


# --- 새로운 엔드포인트 추가: DELETE /me ---


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="회원 탈퇴 (계정 비활성화)",
    description="현재 로그인된 사용자의 계정을 비활성화합니다 (Soft Delete).",
    tags=["사용자 (Users)"],
)
async def deactivate_current_user_account(
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    현재 사용자의 계정을 비활성화(탈퇴 처리)합니다.
    이 작업 후에는 해당 계정으로 더 이상 로그인할 수 없습니다.
    """
    result = await user_service.deactivate_current_user(current_user=current_user)
    return result


# multipart/form-data 처리를 위한 새로운 프로필 업데이트 엔드포인트
@router.post(
    "/me/profile",
    response_model=UserClientProfileResponse,
    summary="사용자 프로필 정보 및 이미지 업데이트 (multipart/form-data)",
    description="사용자 이름(username)과 프로필 이미지 파일을 함께 받아 업데이트합니다. 플러터 클라이언트 전용입니다.",
    tags=["사용자 (Users)"],
)
async def update_current_user_profile_form_data(
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
    # --- Form 필드로 텍스트 데이터 받기 ---
    username: str = Form(...),
    # --- UploadFile로 이미지 파일 받기 (선택적) ---
    profile_image: Optional[UploadFile] = File(None),
):
    """
    multipart/form-data 형식으로 사용자 프로필을 업데이트합니다.
    - **username**: 변경할 사용자 이름 (필수)
    - **profile_image**: 업로드할 프로필 이미지 파일 (선택)
    """
    # 서비스 계층의 새 함수를 호출하여 실제 로직 처리
    updated_user = await user_service.update_user_profile_with_image(
        current_user=current_user,
        username=username,
        profile_image_file=profile_image,
    )
    return updated_user
