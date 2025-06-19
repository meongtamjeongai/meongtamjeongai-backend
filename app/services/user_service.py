# fastapi_backend/app/services/user_service.py
# 사용자 관련 비즈니스 로직을 처리하는 서비스

from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth

from fastapi import UploadFile
from typing import Optional
import uuid

from app.crud import crud_user
from app.models.user import User as UserModel

from app.schemas.user import UserUpdate
from app.schemas.user import UserCreate

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

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """
        시스템의 모든 사용자 목록을 가져옵니다.
        (서비스 계층에서는 권한 검사를 하지 않고, API 계층의 의존성 주입에서 처리)
        """
        return crud_user.get_users(self.db, skip=skip, limit=limit)
    
    def update_user_by_admin(self, *, user_id: int, user_in: UserUpdate) -> UserModel:
        """
        관리자가 사용자의 정보를 업데이트합니다.
        """
        user_to_update = crud_user.get_user(self.db, user_id=user_id)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        
        # UserUpdate 스키마에 정의된 필드만 사용하여 업데이트
        updated_user = crud_user.update_user(self.db, db_user=user_to_update, user_in=user_in)
        return updated_user

    def delete_user_by_admin(self, *, user_id: int) -> dict:
        """
        관리자가 사용자를 DB와 Firebase에서 모두 삭제합니다.
        (기존 deactivate_current_user 로직을 재활용 및 강화)
        """
        user_to_delete = crud_user.get_user(self.db, user_id=user_id)
        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        
        # 1. 연결된 Firebase 계정 삭제
        firebase_uids_to_delete = [
            sa.provider_user_id for sa in user_to_delete.social_accounts
            if sa.provider.value.startswith('firebase_')
        ]

        for uid in firebase_uids_to_delete:
            try:
                firebase_auth.delete_user(uid)
                print(f"SERVICE (delete_user): ✅ Firebase user with UID {uid} has been deleted.")
            except firebase_auth.UserNotFoundError:
                print(f"SERVICE (delete_user): ⚠️ Firebase user with UID {uid} not found, proceeding.")
            except Exception as e:
                print(f"SERVICE (delete_user): ❌ Failed to delete Firebase user {uid}: {e}")
                # Firebase 삭제 실패 시에도 DB 삭제는 진행할지, 아니면 전체 롤백할지 정책 결정 필요
                # 여기서는 에러를 발생시켜 중단
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete Firebase user {uid}: {e}"
                )

        # 2. 우리 DB에서 사용자 완전 삭제 (Hard Delete)
        # cascade 설정에 의해 social_accounts, conversations, user_point 등도 함께 삭제됨
        self.db.delete(user_to_delete)
        self.db.commit()
        
        print(f"SERVICE (delete_user): ✅ User {user_id} and related data have been deleted from DB.")
        
        return {"message": f"User with ID {user_id} has been successfully deleted."}
    
    def create_initial_superuser(self, *, user_in: UserCreate) -> UserModel:
        """
        시스템에 슈퍼유저가 한 명도 없을 경우에만 최초의 슈퍼유저를 생성합니다.
        """
        # DB에 슈퍼유저가 이미 존재하는지 확인
        any_superuser = self.db.query(UserModel).filter(UserModel.is_superuser == True).first()
        if any_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A superuser already exists in the system. Cannot create another initial superuser.",
            )
        
        # crud_user.create_user가 is_superuser, is_active를 처리할 수 있도록 UserCreate 스키마를 사용합니다.
        # UserCreate 스키마에 is_superuser 필드가 없다면 추가하거나, crud 함수를 직접 수정해야 합니다.
        # 여기서는 UserCreate가 해당 필드를 받는다고 가정합니다.
        
        # UserCreate 객체에 슈퍼유저 플래그 설정
        user_in.is_superuser = True
        user_in.is_active = True
        
        # CRUD 함수를 사용하여 사용자 생성
        # (create_user 함수는 내부적으로 비밀번호 해싱 등을 처리)
        new_superuser = crud_user.create_user(self.db, user_in=user_in)
        
        return new_superuser    
    
    def does_superuser_exist(self) -> bool:
        """
        시스템에 슈퍼유저가 한 명이라도 존재하는지 확인하여 bool 값을 반환합니다.
        """
        return self.db.query(UserModel).filter(UserModel.is_superuser == True).first() is not None
    
    # --- ✅ [추가] multipart/form-data를 처리하는 새로운 서비스 메서드 ---
    async def update_user_profile_with_image(
        self,
        *,
        current_user: UserModel,
        username: str,
        profile_image_file: Optional[UploadFile] = None,
    ) -> UserModel:
        """
        사용자 프로필 정보와 이미지 파일을 받아 업데이트합니다.
        1. 이미지가 있으면 S3에 업로드
        2. DB에 사용자 정보(username, image_key) 업데이트
        3. 기존 이미지가 있으면 S3에서 삭제
        """
        s3_image_key = None
        previous_image_key = current_user.profile_image_key

        # 1. 새로운 프로필 이미지가 제공된 경우 S3에 업로드
        if profile_image_file:
            # 파일 내용을 바이트로 읽기
            image_data = await profile_image_file.read()
            # 파일 확장자 가져오기
            file_extension = profile_image_file.filename.split(".")[-1]
            # 고유한 파일명 생성
            filename = f"users/{uuid.uuid4()}.{file_extension}"

            try:
                self.s3_service.upload_bytes_to_s3(
                    data_bytes=image_data,
                    object_key=filename,
                    content_type=profile_image_file.content_type,
                )
                s3_image_key = filename
                print(f"✅ S3 이미지 업로드 성공. Key: {s3_image_key}")
            except Exception as e:
                # S3 업로드 실패 시, 작업을 중단하고 에러 발생
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"S3 이미지 업로드에 실패했습니다: {e}",
                )

        # 2. DB 업데이트를 위한 데이터 준비
        # UserUpdate 스키마를 사용하여 업데이트할 데이터 구성
        update_data = UserUpdate(username=username)
        if s3_image_key:
            # 새 이미지가 업로드된 경우에만 image_key 업데이트
            update_data.profile_image_key = s3_image_key
        
        # DB 업데이트
        updated_user = crud_user.update_user(
            self.db, db_user=current_user, user_in=update_data
        )

        # 3. DB 업데이트 성공 후, 이전 S3 이미지 삭제
        # 새로운 이미지가 등록되었고, 이전 이미지가 존재했다면 삭제
        if s3_image_key and previous_image_key:
            print(f"새로운 프로필 이미지 등록. 이전 이미지 삭제 시도: {previous_image_key}")
            self.s3_service.delete_object(object_key=previous_image_key)

        return updated_user