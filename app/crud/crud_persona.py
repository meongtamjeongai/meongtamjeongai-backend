# app/crud/crud_persona.py
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


async def get_persona(db: AsyncSession, persona_id: int) -> Optional[Persona]:
    """주어진 ID로 페르소나를 조회합니다."""
    stmt = select(Persona).where(Persona.id == persona_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_personas_by_user(
    db: AsyncSession, *, user_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[Persona]:
    """공개 페르소나 및 특정 사용자가 생성한 페르소나 목록을 조회합니다."""
    stmt = select(Persona)
    if user_id:
        stmt = stmt.where(
            or_(Persona.is_public == True, Persona.created_by_user_id == user_id)
        )
    else:
        stmt = stmt.where(Persona.is_public == True)

    stmt = stmt.order_by(Persona.name).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_persona(
    db: AsyncSession, *, persona_in: PersonaCreate, creator_id: Optional[int] = None
) -> Persona:
    """새로운 페르소나를 생성합니다."""
    db_persona_data = persona_in.model_dump(exclude_unset=True)
    db_persona = Persona(**db_persona_data, created_by_user_id=creator_id)
    db.add(db_persona)
    await db.flush()
    await db.refresh(db_persona)
    return db_persona


async def update_persona(
    db: AsyncSession, *, db_persona: Persona, persona_in: PersonaUpdate
) -> Persona:
    """기존 페르소나의 정보를 업데이트합니다."""
    update_data = persona_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(db_persona, field):
            setattr(db_persona, field, value)
    db.add(db_persona)
    await db.flush()
    await db.refresh(db_persona)
    return db_persona


async def delete_persona(db: AsyncSession, *, persona_id: int) -> Optional[Persona]:
    """주어진 ID의 페르소나를 삭제합니다."""
    db_persona = await get_persona(db, persona_id=persona_id)
    if db_persona:
        await db.delete(db_persona)
        await db.flush()
    return db_persona
