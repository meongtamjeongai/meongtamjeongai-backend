# fastapi_backend/app/api/v1/endpoints/messages.py
# 메시지 관련 API 엔드포인트 정의 (대화방 하위 경로)

from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user  # 실제 인증 의존성 함수 임포트
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.message import MessageCreate, MessageResponse
from app.services.message_service import MessageService

# 이 라우터는 /conversations/{conversation_id}/messages 와 같은 경로로 등록될 것임
router = APIRouter()


def get_message_service(db: Session = Depends(get_db)) -> MessageService:
    return MessageService(db)


@router.get(
    "/",  # /conversations/{conversation_id}/messages/ 의 상대 경로
    response_model=List[MessageResponse],
    summary="대화방의 메시지 목록 조회",
    description="특정 대화방의 메시지들을 조회합니다. 본인의 대화방만 접근 가능합니다.",
    tags=["메시지 (Messages)"],
)
async def read_conversation_messages(
    conversation_id: int = Path(
        ..., title="대화방 ID", description="메시지를 조회할 대화방의 ID"
    ),
    skip: int = Query(0, ge=0, description="건너뛸 메시지 수 (페이지네이션)"),
    limit: int = Query(
        100, ge=1, le=200, description="반환할 최대 메시지 수 (페이지네이션)"
    ),
    sort_asc: bool = Query(
        False, description="True면 오래된 순, False면 최신 순(기본값)으로 정렬"
    ),
    message_service: MessageService = Depends(get_message_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    특정 대화방의 메시지 목록을 가져옵니다.
    - **conversation_id**: 경로 파라미터로 받는 대화방 ID.
    - **skip**: 페이지네이션 오프셋.
    - **limit**: 페이지당 메시지 수.
    - **sort_asc**: 정렬 방향 (기본은 최신순).
    """
    # 서비스 계층에서 conversation_id와 current_user.id를 사용하여 권한 확인 및 조회
    messages = message_service.get_messages_for_conversation(
        conversation_id=conversation_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        sort_asc=sort_asc,
    )
    return messages


@router.post(
    "/",  # /conversations/{conversation_id}/messages/ 의 상대 경로
    response_model=List[MessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="새 메시지 전송 및 AI 응답 받기",
    description="대화방에 새 메시지를 전송하고, AI의 응답을 함께 받습니다. 본인의 대화방만 접근 가능합니다.",
    tags=["메시지 (Messages)"],
)
async def send_new_message_in_conversation(
    conversation_id: int = Path(
        ..., title="대화방 ID", description="메시지를 전송할 대화방의 ID"
    ),
    message_in: MessageCreate = Body(...),  # 요청 본문에서 content를 받음
    message_service: MessageService = Depends(get_message_service),
    current_user: UserModel = Depends(get_current_active_user),  # 실제 인증 적용
):
    """
    사용자가 대화방에 새 메시지를 보냅니다. 서버는 이 메시지를 저장하고,
    연결된 페르소나의 AI로부터 응답을 받아 함께 반환합니다.
    - **conversation_id**: 메시지를 보낼 대화방 ID.
    - **Request body (message_in)**:
        - **content**: 사용자가 입력한 메시지 내용.
    """
    if (
        not message_in.content or not message_in.content.strip()
    ):  # 메시지 내용이 비어있는 경우 방지
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty.",
        )

    # 서비스 계층에서 conversation_id와 current_user.id를 사용하여 권한 확인 및 메시지 처리
    # send_new_message는 [user_msg_response, ai_msg_response]를 반환
    message_responses = await message_service.send_new_message(
        conversation_id=conversation_id,
        message_in=message_in,
        current_user=current_user,
    )
    return message_responses
