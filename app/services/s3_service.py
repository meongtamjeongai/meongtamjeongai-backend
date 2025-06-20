# app/services/s3_service.py
import asyncio
import logging

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        # IAM 역할 기반 인증을 사용하므로 Access Key는 필요 없습니다.
        # boto3는 EC2 인스턴스 메타데이터를 통해 자동으로 자격 증명을 찾습니다.
        self.s3_client = boto3.client("s3", region_name="ap-northeast-2")
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_presigned_url(
        self, object_key: str, expiration: int = 3600, for_upload: bool = True
    ) -> str:
        """
        S3 Presigned URL을 생성합니다.
        :param object_key: S3 버킷 내 객체의 경로 (예: 'images/personas/my-image.jpg')
        :param expiration: URL 만료 시간 (초)
        :param for_upload: True이면 PUT용(업로드), False이면 GET용(다운로드) URL을 생성합니다.
        :return: Presigned URL 문자열
        """
        if not self.bucket_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 bucket name is not configured on the server.",
            )

        http_method = "put_object" if for_upload else "get_object"

        try:
            logger.info(
                f"🚀 S3 Presigned URL 생성 시도: Bucket={self.bucket_name}, Key={object_key}, Method={http_method}"
            )
            url = self.s3_client.generate_presigned_url(
                ClientMethod=http_method,
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
                HttpMethod="PUT" if for_upload else "GET",
            )
            logger.info(f"✅ S3 Presigned URL 생성 성공: {url[:70]}...")
            return url

        # ⭐️ [수정] boto3 클라이언트 에러를 더 상세하게 잡습니다.
        except NoCredentialsError:
            # AWS 자격 증명을 전혀 찾지 못한 경우 (가장 흔한 로컬 환경 문제)
            logger.error(
                "🔥🔥🔥 [FATAL] AWS 자격 증명을 찾을 수 없습니다! (NoCredentialsError). "
                "EC2 인스턴스에 IAM 역할이 연결되었는지, 또는 로컬에 AWS 자격증명(~/.aws/credentials)이 설정되었는지 확인하세요.",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server is not configured for AWS access. Please contact administrator.",
            )

        except ClientError as e:
            # 자격 증명은 찾았지만, 권한이 없거나 다른 API 오류가 발생한 경우
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message")
            logger.error(
                f"🔥🔥🔥 S3 Presigned URL 생성 실패 (ClientError): Code={error_code}, Message='{error_message}'",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not generate file URL due to a server-side S3 error: {error_code}",
            )

    # --- 서버에서 직접 바이트 데이터를 업로드하는 함수 ---
    def upload_bytes_to_s3(self, data_bytes: bytes, object_key: str, content_type: str):
        if not self.bucket_name:
            raise HTTPException(...)  # 생략
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data_bytes,
                ContentType=content_type,
            )
        except ClientError as e:
            # 에러 처리 로직
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")

    def delete_object(self, object_key: str) -> bool:
        """
        S3 버킷에서 특정 객체를 삭제합니다.
        :param object_key: 삭제할 객체의 키
        :return: 성공 시 True, 실패 시 False
        """
        if not self.bucket_name:
            logger.error(
                "S3Service: Cannot delete object, bucket name is not configured."
            )
            return False

        try:
            logger.info(
                f"🚀 S3 객체 삭제 시도: Bucket={self.bucket_name}, Key={object_key}"
            )
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"✅ S3 객체 삭제 성공: Key={object_key}")
            return True
        except ClientError as e:
            logger.error(
                f"🔥 S3 객체 삭제 실패 (ClientError): Key={object_key}, Error={e}",
                exc_info=True,
            )
            # 존재하지 않는 객체를 삭제 시도해도 에러가 발생하지 않으므로, 대부분 권한 문제.
            return False

    async def upload_bytes_to_s3_async(
        self, data_bytes: bytes, object_key: str, content_type: str
    ):
        """[비동기] 별도 스레드에서 동기 S3 업로드 함수를 실행합니다."""
        try:
            # asyncio.to_thread를 사용하여 동기 함수를 비동기적으로 실행
            await asyncio.to_thread(
                self.upload_bytes_to_s3, data_bytes, object_key, content_type
            )
        except Exception as e:
            # upload_bytes_to_s3에서 발생한 예외를 여기서 다시 잡아서 처리
            logger.error(f"🔥 S3 비동기 업로드 래퍼에서 오류 발생: {e}", exc_info=True)
            # 이미 HTTPException이 발생했으므로 다시 발생시키거나 새로운 예외를 발생시킴
            raise e


s3_service = S3Service()
