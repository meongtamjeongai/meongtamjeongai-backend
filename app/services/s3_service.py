# app/services/s3_service.py
import logging
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        # IAM 역할 기반 인증을 사용하므로 Access Key는 필요 없습니다.
        # boto3는 EC2 인스턴스 메타데이터를 통해 자동으로 자격 증명을 찾습니다.
        self.s3_client = boto3.client("s3", region_name="ap-northeast-2")
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_presigned_url(self, object_key: str, expiration: int = 3600, for_upload: bool = True) -> str:
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
            url = self.s3_client.generate_presigned_url(
                ClientMethod=http_method,
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
                HttpMethod="PUT" if for_upload else "GET"
            )
            logger.info(f"Successfully generated presigned URL for {object_key} (Method: {http_method.upper()})")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {object_key}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate file upload/download URL.",
            )

s3_service = S3Service()