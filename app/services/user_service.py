# app/services/user_service.py
import uuid
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from firebase_admin import auth as firebase_auth
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_user
from app.models.user import User as UserModel
from app.schemas.user import UserCreate, UserUpdate
from app.services.s3_service import S3Service


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.s3_service = S3Service()

    async def update_user_info(
        self, *, current_user: UserModel, user_in: UserUpdate
    ) -> UserModel:
        """현재 로그인된 사용자의 정보를 업데이트합니다."""
        if user_in.username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username cannot be empty for update.",
            )
        return await crud_user.update_user(
            self.db, db_user=current_user, user_in=user_in
        )

    async def deactivate_current_user(self, *, current_user: UserModel) -> dict:
        """현재 로그인된 사용자의 계정을 비활성화합니다."""
        await crud_user.deactivate_user(self.db, user_to_deactivate=current_user)

        firebase_uids_to_disable = [
            sa.provider_user_id
            for sa in current_user.social_accounts
            if sa.provider.value.startswith("firebase_")
        ]
        for uid in firebase_uids_to_disable:
            try:
                firebase_auth.update_user(uid, disabled=True)
            except Exception as e:
                print(
                    f"SERVICE (deactivate_user): ❌ Failed to disable Firebase user {uid}: {e}"
                )

        return {"message": "User account deactivated successfully."}

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """시스템의 모든 사용자 목록을 가져옵니다."""
        return await crud_user.get_users(self.db, skip=skip, limit=limit)

    async def update_user_by_admin(
        self, *, user_id: int, user_in: UserUpdate
    ) -> UserModel:
        """관리자가 사용자의 정보를 업데이트합니다."""
        user_to_update = await crud_user.get_user(self.db, user_id=user_id)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        return await crud_user.update_user(
            self.db, db_user=user_to_update, user_in=user_in
        )

    async def delete_user_by_admin(self, *, user_id: int) -> dict:
        """관리자가 사용자를 DB와 Firebase에서 모두 삭제합니다."""
        user_to_delete = await crud_user.get_user(self.db, user_id=user_id)
        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        firebase_uids_to_delete = [
            sa.provider_user_id
            for sa in user_to_delete.social_accounts
            if sa.provider.value.startswith("firebase_")
        ]
        for uid in firebase_uids_to_delete:
            try:
                firebase_auth.delete_user(uid)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete Firebase user {uid}: {e}",
                )

        await self.db.delete(user_to_delete)

        return {"message": f"User with ID {user_id} has been successfully deleted."}

    async def create_initial_superuser(self, *, user_in: UserCreate) -> UserModel:
        """시스템에 슈퍼유저가 없을 경우 최초의 슈퍼유저를 생성합니다."""
        any_superuser_stmt = crud_user.select(UserModel).where(
            UserModel.is_superuser == True
        )
        any_superuser = (await self.db.execute(any_superuser_stmt)).scalar_one_or_none()

        if any_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A superuser already exists.",
            )

        user_in.is_superuser = True
        user_in.is_active = True
        return await crud_user.create_user(self.db, user_in=user_in)

    async def does_superuser_exist(self) -> bool:
        """시스템에 슈퍼유저가 한 명이라도 존재하는지 확인합니다."""
        stmt = (
            crud_user.select(UserModel.id)
            .where(UserModel.is_superuser == True)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_user_profile_with_image(
        self,
        *,
        current_user: UserModel,
        username: str,
        profile_image_file: Optional[UploadFile] = None,
    ) -> UserModel:
        """사용자 프로필 정보와 이미지 파일을 받아 업데이트합니다."""
        s3_image_key = None
        previous_image_key = current_user.profile_image_key

        if profile_image_file:
            image_data = await profile_image_file.read()
            file_extension = profile_image_file.filename.split(".")[-1]
            filename = f"users/{uuid.uuid4()}.{file_extension}"
            try:
                self.s3_service.upload_bytes_to_s3(
                    data_bytes=image_data,
                    object_key=filename,
                    content_type=profile_image_file.content_type,
                )
                s3_image_key = filename
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"S3 이미지 업로드에 실패했습니다: {e}",
                )

        update_data = UserUpdate(username=username)
        if s3_image_key:
            update_data.profile_image_key = s3_image_key

        updated_user = await crud_user.update_user(
            self.db, db_user=current_user, user_in=update_data
        )

        if s3_image_key and previous_image_key:
            self.s3_service.delete_object(object_key=previous_image_key)

        return updated_user

    async def get_user_by_id(self, user_id: int) -> UserModel:
        """ID로 사용자를 조회합니다. 없으면 404 에러를 발생시킵니다."""
        db_user = await crud_user.get_user(self.db, user_id=user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return db_user
