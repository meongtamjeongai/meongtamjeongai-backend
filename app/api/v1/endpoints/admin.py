# app/api/v1/endpoints/admin.py

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_superuser
from app.db.session import get_db
from app.schemas.conversation import ConversationAdminResponse, ConversationCreateAdmin
from app.schemas.message import MessageResponse
from app.schemas.phishing import (
    PhishingCaseCreate,
    PhishingCaseResponse,
    PhishingCaseUpdate,
)
from app.schemas.user import (  # 관리자용 응답 스키마
    UserCreate,
    UserDetailResponse,
    UserUpdate,
)
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.phishing_service import PhishingService
from app.services.user_service import UserService

router = APIRouter()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(db)


def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    return MessageService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get(
    "/users",
    response_model=List[UserDetailResponse],
    summary="전체 사용자 목록 조회 (관리자 전용)",
    dependencies=[
        Depends(get_current_active_superuser)
    ],  # ⭐️ 이 라우터의 모든 엔드포인트에 슈퍼유저 권한 강제
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
    dependencies=[Depends(get_current_active_superuser)],
)
def update_user_by_admin(
    user_id: int,
    user_in: UserUpdate,  # 요청 본문으로 수정할 데이터를 받음
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
    dependencies=[Depends(get_current_active_superuser)],
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


@router.post(
    "/initial-superuser",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="최초 슈퍼유저 생성",
    description="시스템에 슈퍼유저가 없을 때만 최초 관리자 계정을 생성합니다.",
    # ⭐️ 중요: 이 엔드포인트는 인증 없이 호출되어야 하므로, 라우터의 전역 의존성을 사용하지 않습니다.
    # 하지만 라우터에 dependencies가 걸려있으므로, 별도 라우터를 만들거나
    # auth.py 같은 다른 곳에 위치시키는 것이 더 나은 설계일 수 있습니다.
    # 여기서는 우선 같은 파일에 두되, 이 점을 인지합니다.
    # -> 더 나은 방법: 이 엔드포인트만 별도의 APIRouter로 만들거나, auth.py로 이동.
    # -> 현실적 대안: 라우터 의존성을 제거하고 각 엔드포인트에 개별적으로 Depends를 추가.
)
def create_initial_superuser(
    user_in: UserCreate,  # email, password를 받음
    user_service: UserService = Depends(get_user_service),
):
    """
    시스템에 슈퍼유저가 존재하지 않을 경우, 제공된 정보로 최초의 슈퍼유저를 생성합니다.
    이미 슈퍼유저가 존재하면 403 Forbidden 에러를 반환합니다.
    """
    # 서비스 계층에서 모든 로직을 처리
    new_superuser = user_service.create_initial_superuser(user_in=user_in)
    return new_superuser


@router.get(
    "/superuser-exists",
    response_model=bool,
    summary="슈퍼유저 존재 여부 확인",
    description="시스템에 슈퍼유저가 한 명이라도 존재하는지 확인합니다. 인증이 필요 없습니다.",
)
def check_superuser_existence(
    user_service: UserService = Depends(get_user_service),
):
    """
    Returns `true` if at least one superuser exists, otherwise `false`.
    """
    return user_service.does_superuser_exist()


# --- 대화방 관리 API (관리자 전용) ---


@router.get(
    "/conversations",
    response_model=List[ConversationAdminResponse],
    summary="전체 대화방 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def read_all_conversations(
    skip: int = 0,
    limit: int = 100,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """시스템의 모든 대화방 목록을 조회합니다."""
    return conversation_service.get_all_conversations_admin(skip=skip, limit=limit)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="특정 대화방의 메시지 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def read_conversation_messages_admin(
    conversation_id: int,
    message_service: MessageService = Depends(get_message_service),
):
    """관리자가 특정 대화방의 모든 메시지를 조회합니다."""
    # 관리자 화면에서는 대화 전체를 보는 경우가 많으므로 limit을 넉넉하게 설정
    return message_service.get_messages_for_conversation_admin(
        conversation_id=conversation_id, skip=0, limit=500
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="대화방 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_conversation_by_admin(
    conversation_id: int,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """관리자가 특정 대화방을 ID로 영구 삭제합니다."""
    conversation_service.delete_conversation_admin(conversation_id=conversation_id)
    return {
        "message": f"Conversation with ID {conversation_id} has been successfully deleted."
    }


# 👇 관리자용 대화방 생성 API 엔드포인트
@router.post(
    "/conversations",
    response_model=ConversationAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="대화방 생성 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def create_conversation_by_admin(
    conversation_in: ConversationCreateAdmin,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """관리자가 특정 사용자와 페르소나를 지정하여 새 대화방을 생성합니다."""
    return conversation_service.start_new_conversation_admin(
        conversation_in=conversation_in
    )


def get_phishing_service(db: Session = Depends(get_db)) -> PhishingService:
    return PhishingService(db)


# --- 피싱 사례 관리 API (관리자 전용) ---


@router.post(
    "/phishing-cases",
    response_model=PhishingCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 피싱 사례 생성 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def create_phishing_case_by_admin(
    case_in: PhishingCaseCreate,
    service: PhishingService = Depends(get_phishing_service),
):
    return service.create_new_case(case_in=case_in)


@router.put(
    "/phishing-cases/{case_id}",
    response_model=PhishingCaseResponse,
    summary="피싱 사례 수정 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def update_phishing_case_by_admin(
    case_id: int,
    case_in: PhishingCaseUpdate,
    service: PhishingService = Depends(get_phishing_service),
):
    return service.update_existing_case(case_id=case_id, case_in=case_in)


@router.delete(
    "/phishing-cases/{case_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="피싱 사례 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_phishing_case_by_admin(
    case_id: int, service: PhishingService = Depends(get_phishing_service)
):
    service.delete_case(case_id=case_id)
    return {
        "message": f"Phishing case with ID {case_id} has been successfully deleted."
    }
