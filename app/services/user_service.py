# fastapi_backend/app/services/user_service.py
# 사용자 관련 비즈니스 로직을 처리하는 서비스

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import firebase_admin
from firebase_admin import auth as firebase_auth

from app.crud import crud_user
from app.models.user import User as UserModel
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def update_user_info(self, *, current_user: UserModel, user_in: UserUpdate) -> UserModel:
        """
        현재 로그인된 사용자의 정보를 업데이트합니다.
        (현재는 username만 업데이트 가능하도록 제한)
        """
        # email, password 등 민감 정보 업데이트는 별도 로직/검증이 필요할 수 있음
        # 여기서는 username 업데이트만 간단히 구현
        if user_in.username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty for update."
            )

        # username 중복 검사 등 추가 로직 가능
        # ...

        updated_user = crud_user.update_user(
            self.db, db_user=current_user, user_in=user_in)
        return updated_user

    def deactivate_current_user(self, *, current_user: UserModel) -> dict:
        """
        현재 로그인된 사용자의 계정을 비활성화합니다.
        우리 DB와 Firebase 양쪽 모두 처리합니다.
        """
        # 1. 우리 DB에서 사용자 비활성화 (is_active = False)
        crud_user.deactivate_user(self.db, user_to_deactivate=current_user)
        print(
            f"SERVICE (deactivate_user): User {current_user.id} has been deactivated in DB.")

        # 2. 연결된 Firebase 계정 비활성화
        firebase_uids_to_disable = [
            sa.provider_user_id for sa in current_user.social_accounts
            if sa.provider.value.startswith('firebase_')
        ]

        for uid in firebase_uids_to_disable:
            try:
                firebase_auth.update_user(uid, disabled=True)
                print(
                    f"SERVICE (deactivate_user): ✅ Firebase user with UID {uid} has been disabled.")
            except firebase_auth.UserNotFoundError:
                print(
                    f"SERVICE (deactivate_user): ⚠️ Firebase user with UID {uid} not found.")
            except Exception as e:
                print(
                    f"SERVICE (deactivate_user): ❌ Failed to disable Firebase user {uid}: {e}")
                # 중요: 이 경우 DB는 비활성화되었지만 Firebase는 아닐 수 있음.
                # 프로덕션에서는 이를 처리하는 추가 정책(예: 재시도 큐)이 필요할 수 있음.

        return {"message": "User account deactivated successfully."}
