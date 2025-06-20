# fastapi_backend/app/api/v1/endpoints/personas.py
# 페르소나 관련 API 엔드포인트 정의

from typing import List, Optional

from fastapi import (  # Path 임포트 추가
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user
from app.db.session import get_async_db
from app.models.user import User as UserModel
from app.schemas.persona import PersonaCreate, PersonaResponse, PersonaUpdate
from app.services.persona_service import PersonaService

router = APIRouter()


async def get_persona_service(db: Session = Depends(get_async_db)) -> PersonaService:
    return PersonaService(db)


# --- GET / (목록 조회) - 이전과 동일 ---
@router.get(
    "/",
    response_model=List[PersonaResponse],
    summary="페르소나 목록 조회",
    tags=["페르소나 (Personas)"],
)
async def read_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    persona_service: PersonaService = Depends(get_persona_service),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    personas = await persona_service.get_all_personas_for_user(
        current_user=current_user, skip=skip, limit=limit
    )

    return personas


# --- POST / (생성) - 이전과 동일 ---
@router.post(
    "/",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 페르소나 생성",
    tags=["페르소나 (Personas)"],
)
async def create_new_persona(
    persona_in: PersonaCreate,
    persona_service: PersonaService = Depends(get_persona_service),
    current_user: UserModel = Depends(get_current_active_user),
):
    return persona_service.create_new_persona(
        persona_in=persona_in, creator=current_user
    )


# --- GET /{id} (상세 조회) - 이전과 동일 ---
@router.get(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="특정 페르소나 상세 조회",
    tags=["페르소나 (Personas)"],
)
async def read_persona_by_id(
    persona_id: int = Path(..., title="페르소나 ID"),  # Path 사용 명시
    persona_service: PersonaService = Depends(get_persona_service),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    db_persona = persona_service.get_persona_by_id(persona_id=persona_id)
    if db_persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )

    if not db_persona.is_public:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if (
            db_persona.created_by_user_id != current_user.id
            and not current_user.is_superuser
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )

    return db_persona


# --- PUT /{id} (수정) - 새로운 엔드포인트 ---
@router.put(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="페르소나 수정",
    description="지정된 ID의 페르소나를 수정합니다. 페르소나 생성자 또는 관리자만 가능합니다.",
    tags=["페르소나 (Personas)"],
)
async def update_persona_by_id(
    persona_id: int = Path(..., title="수정할 페르소나 ID"),
    persona_in: PersonaUpdate = None,  # 요청 본문에서 수정할 데이터 받음
    persona_service: PersonaService = Depends(get_persona_service),
    current_user: UserModel = Depends(
        get_current_active_user
    ),  # 수정은 반드시 로그인 필요
):
    """
    페르소나 정보를 업데이트합니다.
    - **persona_id**: 수정할 페르소나의 ID.
    - **Request Body**: `PersonaUpdate` 스키마에 맞는 수정할 필드들.
    """
    updated_persona = persona_service.update_existing_persona(
        persona_id=persona_id, persona_in=persona_in, current_user=current_user
    )
    if updated_persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    # 권한 오류는 서비스 계층에서 403 예외를 발생시키므로 여기서는 404만 처리
    return updated_persona


# --- DELETE /{id} (삭제) - 새로운 엔드포인트 ---
@router.delete(
    "/{persona_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="페르소나 삭제",
    description="지정된 ID의 페르소나를 삭제합니다. 페르소나 생성자 또는 관리자만 가능합니다.",
    tags=["페르소나 (Personas)"],
)
async def delete_persona_by_id(
    persona_id: int = Path(..., title="삭제할 페르소나 ID"),
    persona_service: PersonaService = Depends(get_persona_service),
    current_user: UserModel = Depends(
        get_current_active_user
    ),  # 삭제는 반드시 로그인 필요
):
    """
    페르소나를 삭제합니다.
    - **persona_id**: 삭제할 페르소나의 ID.
    """
    deleted_persona = persona_service.delete_existing_persona(
        persona_id=persona_id, current_user=current_user
    )
    if deleted_persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    # 권한 오류는 서비스 계층에서 403 예외 발생
    # 성공 시 204 No Content 응답이 자동으로 반환됨
    return None
