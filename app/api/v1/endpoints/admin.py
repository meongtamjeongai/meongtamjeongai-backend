# app/api/v1/endpoints/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_superuser
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.user import UserDetailResponse,UserUpdate # 관리자용 응답 스키마
from app.services.user_service import UserService

router = APIRouter()

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@router.get(
    "/users",
    response_model=List[UserDetailResponse],
    summary="전체 사용자 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)] # ⭐️ 이 라우터의 모든 엔드포인트에 슈퍼유저 권한 강제
)
def read_all_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
):
    """
    시스템의 모든 사용자 목록을 조회합니다. 슈퍼유저만 접근 가능합니다.
    """
    users = user_service.get_all_users(skip=skip, limit=limit)
    return users

@router.put(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="사용자 정보 수정 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)]
)
def update_user_by_admin(
    user_id: int,
    user_in: UserUpdate, # 요청 본문으로 수정할 데이터를 받음
    user_service: UserService = Depends(get_user_service),
):
    """
    관리자가 특정 사용자의 정보를 수정합니다 (username, is_active, is_superuser 등).
    """
    updated_user = user_service.update_user_by_admin(user_id=user_id, user_in=user_in)
    return updated_user

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="사용자 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)]
)
def delete_user_by_admin(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
):
    """
    관리자가 특정 사용자를 DB와 Firebase에서 모두 삭제합니다.
    """
    result = user_service.delete_user_by_admin(user_id=user_id)
    return result