# fastapi_backend/app/api/v1/endpoints/conversations.py
# 대화방 및 해당 대화방의 메시지 관련 API 엔드포인트 정의

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user  # 실제 인증 의존성 함수 임포트

# 메시지 관련 라우터 임포트
from app.api.v1.endpoints import messages as messages_router
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.services.conversation_service import ConversationService

router = APIRouter()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(db)


@router.get(
    "/",
    response_model=List[ConversationResponse],
    summary="사용자의 대화방 목록 조회",
    description="현재 로그인된 사용자의 모든 대화방 목록을 반환합니다.",
    tags=["대화방 (Conversations)"],
)
async def read_user_conversations(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수 (페이지네이션)"),
    limit: int = Query(
        100, ge=1, le=200, description="반환할 최대 항목 수 (페이지네이션)"
    ),
    conversation_service: ConversationService = Depends(get_conversation_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    현재 사용자의 대화방 목록을 조회합니다. `last_message_at` 기준으로 내림차순 정렬됩니다.
    """
    conversations = conversation_service.get_all_conversations_for_user(
        current_user=current_user, skip=skip, limit=limit
    )
    return conversations


@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 대화방 생성",
    description="새로운 대화방을 생성합니다.",
    tags=["대화방 (Conversations)"],
)
async def create_new_conversation(
    conversation_in: ConversationCreate,
    conversation_service: ConversationService = Depends(get_conversation_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    새로운 대화방을 생성합니다.
    - **persona_id**: 대화할 페르소나의 ID (필수)
    - **title**: 대화방 제목 (선택)
    """
    return conversation_service.start_new_conversation(
        conversation_in=conversation_in, current_user=current_user
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="특정 대화방 상세 조회",
    description="ID로 특정 대화방의 상세 정보를 조회합니다. 본인의 대화방만 접근 가능합니다.",
    tags=["대화방 (Conversations)"],
)
async def read_conversation_by_id(
    conversation_id: int = Path(
        ..., title="대화방 ID", description="조회할 대화방의 ID"
    ),
    conversation_service: ConversationService = Depends(get_conversation_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    특정 대화방의 상세 정보를 가져옵니다.
    (현재는 메시지 목록은 별도 API로 조회)
    """
    # 서비스 계층에서 conversation_id와 current_user.id를 사용하여 권한 확인 및 조회
    db_conversation = conversation_service.get_conversation_by_id_for_user(
        conversation_id=conversation_id, current_user=current_user
    )
    # get_conversation_by_id_for_user 내부에서 찾지 못하면 404 발생
    return db_conversation


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,  # 성공 시 내용 없음
    summary="대화방 삭제",
    description="특정 대화방을 삭제합니다. 본인의 대화방만 삭제 가능합니다.",
    tags=["대화방 (Conversations)"],
)
async def delete_user_conversation(
    conversation_id: int = Path(
        ..., title="대화방 ID", description="삭제할 대화방의 ID"
    ),
    conversation_service: ConversationService = Depends(get_conversation_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    사용자의 특정 대화방을 삭제합니다. 관련된 모든 메시지도 함께 삭제됩니다.
    """
    deleted_conversation = conversation_service.delete_existing_conversation(
        conversation_id=conversation_id, current_user=current_user
    )
    # delete_existing_conversation 내부에서 권한 및 존재 여부 확인 후 404 또는 403 발생 가능
    if not deleted_conversation:
        # 이 경우는 서비스에서 None을 반환했으나, 실제로는 서비스 내에서 이미 HTTPException을 발생시켰어야 함.
        # 방어적으로 추가.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or could not be deleted",
        )
    return None  # 204 No Content 응답


# --- 메시지 라우터 포함 ---
# /conversations/{conversation_id}/messages 경로를 위해 messages_router.router를 현재 라우터에 포함
# messages.py 내부의 엔드포인트들은 이 conversation_id를 Path 파라미터로 사용합니다.
router.include_router(
    messages_router.router,  # messages.py에서 정의한 APIRouter 인스턴스
    prefix="/{conversation_id}/messages",  # 이 접두사가 붙음
    # tags=["메시지 (Messages)"] # 태그는 messages.py 내부에서 이미 정의했으므로 중복 불필요
)
