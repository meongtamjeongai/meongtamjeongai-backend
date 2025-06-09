# fastapi_backend/app/services/persona_service.py
# 페르소나 관련 비즈니스 로직을 처리하는 서비스

from typing import List, Optional

from fastapi import HTTPException, status  # HTTPException, status 임포트
from sqlalchemy.orm import Session

from app.crud import crud_persona
from app.models.persona import Persona
from app.models.user import User as UserModel  # UserModel로 별칭 사용
from app.schemas.persona import PersonaCreate, PersonaUpdate


class PersonaService:
    def __init__(self, db: Session):
        self.db = db

    def get_persona_by_id(self, persona_id: int) -> Optional[Persona]:
        """ID로 특정 페르소나 조회"""
        return crud_persona.get_persona(self.db, persona_id=persona_id)

    def get_all_personas_for_user(
        self, current_user: Optional[UserModel], skip: int = 0, limit: int = 100
    ) -> List[Persona]:
        """
        현재 사용자를 기준으로 페르소나 목록을 가져옵니다.
        로그인한 사용자는 자신이 만든 페르소나와 공개 페르소나를 볼 수 있습니다.
        로그인하지 않은 사용자는 공개 페르소나만 볼 수 있습니다.
        """
        user_id_to_filter = current_user.id if current_user else None
        return crud_persona.get_personas_by_user(
            self.db, user_id=user_id_to_filter, skip=skip, limit=limit
        )

    def create_new_persona(
        self, persona_in: PersonaCreate, creator: UserModel
    ) -> Persona:
        """
        새로운 페르소나를 생성합니다. (creator는 필수)
        """
        creator_id = creator.id
        return crud_persona.create_persona(
            self.db, persona_in=persona_in, creator_id=creator_id
        )

    def update_existing_persona(
        self, persona_id: int, persona_in: PersonaUpdate, current_user: UserModel
    ) -> Optional[Persona]:
        """
        기존 페르소나를 업데이트합니다.
        본인이 생성한 페르소나 또는 슈퍼유저만 수정 가능합니다.
        """
        db_persona = crud_persona.get_persona(self.db, persona_id=persona_id)
        if not db_persona:
            return None  # 엔드포인트에서 404 처리

        # --- 권한 검사 로직 추가 ---
        # 슈퍼유저가 아니고, 페르소나 생성자도 아니라면 권한 없음 오류 발생
        if not current_user.is_superuser and (
            db_persona.created_by_user_id != current_user.id
        ):
            print(
                f"SERVICE (update_persona): User {current_user.id} is not authorized to update persona {persona_id}."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this persona",
            )

        return crud_persona.update_persona(
            self.db, db_persona=db_persona, persona_in=persona_in
        )

    def delete_existing_persona(
        self, persona_id: int, current_user: UserModel
    ) -> Optional[Persona]:
        """
        페르소나를 삭제합니다.
        본인이 생성한 페르소나 또는 슈퍼유저만 삭제 가능합니다.
        """
        db_persona = crud_persona.get_persona(self.db, persona_id=persona_id)
        if not db_persona:
            return None  # 엔드포인트에서 404 처리

        # --- 권한 검사 로직 추가 ---
        if not current_user.is_superuser and (
            db_persona.created_by_user_id != current_user.id
        ):
            print(
                f"SERVICE (delete_persona): User {current_user.id} is not authorized to delete persona {persona_id}."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this persona",
            )

        return crud_persona.delete_persona(self.db, persona_id=persona_id)
