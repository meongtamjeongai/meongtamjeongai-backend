# app/services/persona_service.py
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_persona
from app.models.persona import Persona
from app.models.user import User as UserModel
from app.schemas.persona import PersonaCreate, PersonaUpdate


class PersonaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_persona_by_id(self, persona_id: int) -> Optional[Persona]:
        """ID로 특정 페르소나 조회"""
        return await crud_persona.get_persona(self.db, persona_id=persona_id)

    async def get_all_personas_for_user(
        self, current_user: Optional[UserModel], skip: int = 0, limit: int = 100
    ) -> List[Persona]:
        """현재 사용자를 기준으로 페르소나 목록을 가져옵니다."""
        user_id_to_filter = current_user.id if current_user else None
        return await crud_persona.get_personas_by_user(
            self.db, user_id=user_id_to_filter, skip=skip, limit=limit
        )

    async def create_new_persona(
        self, persona_in: PersonaCreate, creator: UserModel
    ) -> Persona:
        """새로운 페르소나를 생성합니다."""
        return await crud_persona.create_persona(
            self.db, persona_in=persona_in, creator_id=creator.id
        )

    async def update_existing_persona(
        self, persona_id: int, persona_in: PersonaUpdate, current_user: UserModel
    ) -> Optional[Persona]:
        """기존 페르소나를 업데이트합니다."""
        db_persona = await crud_persona.get_persona(self.db, persona_id=persona_id)
        if not db_persona:
            return None

        if not current_user.is_superuser and (
            db_persona.created_by_user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this persona",
            )

        return await crud_persona.update_persona(
            self.db, db_persona=db_persona, persona_in=persona_in
        )

    async def delete_existing_persona(
        self, persona_id: int, current_user: UserModel
    ) -> Optional[Persona]:
        """페르소나를 삭제합니다."""
        db_persona = await crud_persona.get_persona(self.db, persona_id=persona_id)
        if not db_persona:
            return None

        if not current_user.is_superuser and (
            db_persona.created_by_user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this persona",
            )

        return await crud_persona.delete_persona(self.db, persona_id=persona_id)
