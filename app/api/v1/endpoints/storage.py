# app/api/v1/endpoints/storage.py
import enum
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_superuser, get_current_active_user
from app.models.user import User as UserModel
from app.services.s3_service import S3Service

router = APIRouter()


# 업로드 카테고리를 명확히 정의하는 Enum 클래스
class UploadCategory(str, enum.Enum):
    """
    S3에 업로드될 파일의 종류를 정의합니다.
    이 값은 S3 내의 폴더 경로로 사용됩니다.
    """

    USERS = "users"
    PERSONAS = "personas"


# Presigned URL 요청 시 클라이언트가 보낼 데이터 형식
class PresignedUrlRequest(BaseModel):
    filename: str = Field(
        ...,
        description="업로드할 파일의 원래 이름 (예: my_avatar.png)",
        examples=["my_profile.jpg"],
    )


# 서버가 클라이언트에게 반환할 Presigned URL 응답 형식
class PresignedUrlResponse(BaseModel):
    url: str = Field(
        ..., description="생성된 Presigned URL (이 URL로 직접 파일 업로드/다운로드)"
    )
    object_key: str = Field(..., description="S3에 저장될 객체의 최종 경로(key)")


@router.post(
    "/presigned-url/upload",
    response_model=PresignedUrlResponse,
    summary="파일 업로드를 위한 Presigned URL 생성",
    description="클라이언트가 S3에 직접 파일을 업로드할 수 있는 임시 URL(PUT)을 발급합니다. 업로드는 인증된 사용자만 가능합니다.",
)
def get_upload_presigned_url(
    request_body: PresignedUrlRequest,
    category: UploadCategory = Query(
        ..., description="업로드 종류 (users: 사용자 프로필, personas: 페르소나 프로필)"
    ),
    s3_service: S3Service = Depends(S3Service),
    # 이 엔드포인트는 인증이 필요함을 명시
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    클라이언트가 S3에 직접 파일을 업로드할 수 있는 임시 URL을 발급받습니다.

    - **category**: 'users' 또는 'personas' 중 하나를 지정하여 어떤 종류의 이미지인지 명시합니다.
    - **filename**: 업로드할 파일의 원래 이름. 확장자를 포함해야 합니다.

    반환된 `object_key`는 파일 업로드 성공 후, 관련 모델(User, Persona)을 업데이트할 때 사용해야 합니다.
    """
    # 파일 확장자 추출 (예: 'my_avatar.png' -> 'png')
    file_extension = request_body.filename.split(".")[-1]

    # category 값에 따라 동적으로 S3 경로(Object Key) 생성
    # 예: 'users/images/9a8b7c6d-....-uuid.png' 또는 'personas/images/....-uuid.png'
    # 이렇게 하면 S3 버킷 내에서 파일들이 체계적으로 정리됩니다.
    object_key = f"{category.value}/images/{uuid.uuid4()}.{file_extension}"

    # S3 서비스를 사용하여 업로드용(PUT) Presigned URL 생성
    url = s3_service.generate_presigned_url(object_key=object_key, for_upload=True)

    return PresignedUrlResponse(url=url, object_key=object_key)


@router.get(
    "/presigned-url/download",
    response_model=PresignedUrlResponse,
    summary="파일 조회를 위한 Presigned URL 생성",
    description="S3에 저장된 비공개 파일을 조회할 수 있는 임시 URL(GET)을 발급합니다. 이 URL은 누구나 접근 가능하므로 주의해서 사용해야 합니다.",
)
def get_download_presigned_url(
    object_key: str = Query(..., description="조회할 파일의 S3 객체 키"),
    s3_service: S3Service = Depends(S3Service),
):
    """
    S3에 저장된 비공개 파일을 조회(다운로드)할 수 있는 임시 URL을 발급받습니다.

    - **object_key**: 다운로드할 파일의 전체 경로(key). (예: 'users/images/some-uuid.png')

    이 URL은 짧은 만료 시간을 가지며, 비공개 S3 객체에 대한 임시 접근 권한을 부여합니다.
    """
    # S3 서비스를 사용하여 다운로드용(GET) Presigned URL 생성
    url = s3_service.generate_presigned_url(object_key=object_key, for_upload=False)

    return PresignedUrlResponse(url=url, object_key=object_key)


@router.delete(
    "/object",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="S3 객체 삭제 (관리자 전용)",
    dependencies=[Depends(get_current_active_superuser)],  # 관리자만 호출 가능
)
def delete_s3_storage_object(
    object_key: str = Query(..., description="삭제할 파일의 S3 객체 키"),
    s3_service: S3Service = Depends(S3Service),
):
    """
    S3 버킷에서 특정 객체를 영구적으로 삭제합니다.
    """
    success = s3_service.delete_object(object_key=object_key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete object '{object_key}' from S3.",
        )
    return None  # 성공 시 204 No Content 응답
