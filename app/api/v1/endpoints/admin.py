# app/api/v1/endpoints/admin.py
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api.deps import (
    HasScope,
    get_current_active_superuser,
    get_current_principal,
)
from app.db.session import get_async_db
from app.models.user import User as UserModel
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    NewApiKeyResponse,
)
from app.schemas.conversation import ConversationAdminResponse, ConversationCreateAdmin
from app.schemas.message import MessageResponse
from app.schemas.phishing import (
    PhishingCaseCreate,
    PhishingCaseResponse,
    PhishingCaseUpdate,
)
from app.schemas.user import UserCreate, UserDetailResponse, UserUpdate
from app.services.api_key_service import ApiKeyService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.phishing_service import PhishingService
from app.services.user_service import UserService

router = APIRouter(tags=["관리자 (Admin)"])


async def get_conversation_service(db: AsyncSession = Depends(get_async_db)) -> ConversationService:
    return ConversationService(db)


async def get_message_service(db: AsyncSession = Depends(get_async_db)) -> MessageService:
    return MessageService(db)


async def get_user_service(db: AsyncSession = Depends(get_async_db)) -> UserService:
    return UserService(db)


async def get_phishing_service(db: AsyncSession = Depends(get_async_db)) -> PhishingService:
    return PhishingService(db)


async def get_api_key_service(db: AsyncSession = Depends(get_async_db)) -> ApiKeyService:
    return ApiKeyService(db)


@router.get(
    "/users",
    response_model=List[UserDetailResponse],
    summary="전체 사용자 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def read_all_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
):
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return users


@router.put(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="사용자 정보 수정 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_user_by_admin(
    user_id: int,
    user_in: UserUpdate,
    user_service: UserService = Depends(get_user_service),
):
    updated_user = await user_service.update_user_by_admin(user_id=user_id, user_in=user_in)
    return updated_user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="사용자 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_user_by_admin(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
):
    result = await user_service.delete_user_by_admin(user_id=user_id)
    return result


@router.post(
    "/initial-superuser",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="최초 슈퍼유저 생성",
)
async def create_initial_superuser(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    new_superuser = await user_service.create_initial_superuser(user_in=user_in)
    return new_superuser


@router.get(
    "/superuser-exists",
    response_model=bool,
    summary="슈퍼유저 존재 여부 확인",
)
async def check_superuser_existence(
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.does_superuser_exist()


@router.get(
    "/conversations",
    response_model=List[ConversationAdminResponse],
    summary="전체 대화방 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def read_all_conversations(
    skip: int = 0,
    limit: int = 100,
    conversation_service: ConversationService = Depends(
        get_conversation_service),
):
    return await conversation_service.get_all_conversations_admin(skip=skip, limit=limit)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="특정 대화방의 메시지 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def read_conversation_messages_admin(
    conversation_id: int,
    message_service: MessageService = Depends(get_message_service),
):
    return await message_service.get_messages_for_conversation_admin(
        conversation_id=conversation_id, skip=0, limit=500
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="대화방 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_conversation_by_admin(
    conversation_id: int,
    conversation_service: ConversationService = Depends(
        get_conversation_service),
):
    await conversation_service.delete_conversation_admin(conversation_id=conversation_id)
    return {"message": f"Conversation with ID {conversation_id} has been successfully deleted."}


@router.post(
    "/conversations",
    response_model=ConversationAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="대화방 생성 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def create_conversation_by_admin(
    conversation_in: ConversationCreateAdmin,
    conversation_service: ConversationService = Depends(
        get_conversation_service),
):
    return await conversation_service.start_new_conversation_admin(conversation_in=conversation_in)


@router.post(
    "/api-keys",
    response_model=NewApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 API 키 발급 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def issue_new_api_key(
    api_key_in: ApiKeyCreate,
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: UserModel = Depends(get_current_active_superuser),
):
    db_api_key, plain_api_key = await service.create_api_key(
        api_key_in=api_key_in, current_user=current_user
    )
    return NewApiKeyResponse(**db_api_key.__dict__, api_key=plain_api_key)


@router.get(
    "/api-keys",
    response_model=List[ApiKeyResponse],
    summary="발급된 API 키 목록 조회 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def get_issued_api_keys(
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_async_db),
):
    api_keys = await crud.crud_api_key.get_api_keys_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return api_keys


@router.delete(
    "/api-keys/{key_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="API 키 폐기 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def revoke_api_key(
    key_id: int,
    service: ApiKeyService = Depends(get_api_key_service),
    current_user: UserModel = Depends(get_current_active_superuser),
):
    await service.revoke_api_key(api_key_id=key_id, current_user=current_user)
    return {"message": f"API Key with ID {key_id} has been successfully deactivated."}


@router.post(
    "/phishing-cases",
    response_model=PhishingCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 피싱 사례 생성 (관리자 또는 API 키)",
    dependencies=[Depends(HasScope(required_scopes=["phishing:create"]))],
)
async def create_phishing_case_by_admin(
    case_in: PhishingCaseCreate,
    service: PhishingService = Depends(get_phishing_service),
):
    return await service.create_new_case(case_in=case_in)


@router.put(
    "/phishing-cases/{case_id}",
    response_model=PhishingCaseResponse,
    summary="피싱 사례 수정 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_phishing_case_by_admin(
    case_id: int,
    case_in: PhishingCaseUpdate,
    service: PhishingService = Depends(get_phishing_service),
):
    return await service.update_existing_case(case_id=case_id, case_in=case_in)


@router.delete(
    "/phishing-cases/{case_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="피싱 사례 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_phishing_case_by_admin(
    case_id: int, service: PhishingService = Depends(get_phishing_service)
):
    await service.delete_case(case_id=case_id)
    return {"message": f"Phishing case with ID {case_id} has been successfully deleted."}
