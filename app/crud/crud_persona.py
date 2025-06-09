# fastapi_backend/app/crud/crud_persona.py
# Persona 모델에 대한 CRUD 작업을 위한 함수들

from typing import List, Optional

from sqlalchemy import or_  # 공개 페르소나 + 사용자 생성 페르소나 조회를 위해
from sqlalchemy.orm import Session

from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


def get_persona(db: Session, persona_id: int) -> Optional[Persona]:
    """주어진 ID로 페르소나를 조회합니다."""
    return db.query(Persona).filter(Persona.id == persona_id).first()


def get_personas_by_user(
    db: Session, *, user_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[Persona]:
    """
    페르소나 목록을 조회합니다.
    user_id가 제공되면 해당 사용자가 생성한 페르소나와 공개 페르소나를 함께 반환합니다.
    user_id가 없으면 공개 페르소나만 반환합니다.
    """
    query = db.query(Persona)
    if user_id:
        # 공개 페르소나 또는 해당 사용자가 만든 페르소나
        query = query.filter(
            or_(Persona.is_public == True, Persona.created_by_user_id == user_id)
        )
    else:
        # 공개 페르소나만
        query = query.filter(Persona.is_public == True)

    return query.order_by(Persona.name).offset(skip).limit(limit).all()


def create_persona(
    db: Session, *, persona_in: PersonaCreate, creator_id: Optional[int] = None
) -> Persona:
    """
    새로운 페르소나를 생성합니다.
    creator_id가 제공되면 해당 사용자가 페르소나를 생성한 것으로 기록합니다.
    """
    db_persona_data = persona_in.model_dump(exclude_unset=True)
    db_persona = Persona(**db_persona_data, created_by_user_id=creator_id)
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


def update_persona(
    db: Session, *, db_persona: Persona, persona_in: PersonaUpdate
) -> Persona:
    """기존 페르소나의 정보를 업데이트합니다."""
    update_data = persona_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(db_persona, field):
            setattr(db_persona, field, value)
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


def delete_persona(
    db: Session, *, persona_id: int, user_id: Optional[int] = None
) -> Optional[Persona]:
    """
    주어진 ID의 페르소나를 삭제합니다.
    user_id가 제공되면 해당 사용자가 생성한 페르소나만 삭제하도록 제한할 수 있습니다 (선택적).
    is_public이 False인 페르소나만 삭제 가능하도록 하거나, 관리자만 삭제 가능하도록 할 수도 있습니다.
    """
    db_persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if db_persona:
        # 삭제 권한 체크 로직 (예시)
        # if user_id and db_persona.created_by_user_id != user_id:
        #     # 본인이 생성한 페르소나가 아니면 삭제 불가
        #     return None
        # if db_persona.is_public and not is_admin(user_id): # is_admin 함수는 별도 구현 필요
        #     # 공개 페르소나는 관리자만 삭제 가능
        #     return None

        db.delete(db_persona)
        db.commit()
        return db_persona
    return None


# `app/crud/__init__.py` 파일에 다음을 추가합니다:
# from . import crud_persona
# 또는 from .crud_persona import get_persona, create_persona 등
