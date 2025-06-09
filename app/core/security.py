# fastapi_backend/app/core/security.py
# 보안 관련 유틸리티 함수 (비밀번호 해싱, JWT 생성 및 검증 등)

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext  # 비밀번호 해싱용

from app.core.config import settings  # 설정값 가져오기
from app.schemas.token import TokenPayload  # 토큰 페이로드 스키마

# 비밀번호 해싱을 위한 Passlib 컨텍스트 설정
# bcrypt 알고리즘 사용, deprecated="auto"는 bcrypt가 지원되지 않을 경우 다른 알고리즘 자동 선택
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
JWT_SECRET_KEY = settings.SECRET_KEY  # Access Token용 비밀키
JWT_REFRESH_SECRET_KEY = (
    f"{settings.SECRET_KEY}_refresh"  # Refresh Token용 별도 비밀키 (선택적이지만 권장)
)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    주어진 subject(사용자 식별자)와 만료 시간으로 Access Token을 생성합니다.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    # 추가적인 클레임이 있다면 여기에 추가 가능: to_encode.update({"custom_claim": "value"})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    주어진 subject(사용자 식별자)와 만료 시간으로 Refresh Token을 생성합니다.
    Refresh Token은 일반적으로 Access Token보다 긴 유효 기간을 가집니다.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }  # 'type' 클레임 추가 (선택적)
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(
    token: str, secret_key: str, algorithm: str = ALGORITHM
) -> Optional[TokenPayload]:
    """
    주어진 토큰을 검증하고 페이로드를 반환합니다. 유효하지 않으면 None을 반환합니다.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        # 토큰 페이로드 스키마로 유효성 검사 (선택적이지만 권장)
        # token_data = TokenPayload(**payload) # TokenPayload 스키마에 맞는지 확인
        # 여기서는 sub만 추출하여 TokenPayload 형태로 반환 (또는 전체 payload 반환 후 서비스에서 처리)
        return TokenPayload(sub=payload.get("sub"))  # sub 클레임만 사용
    except JWTError as e:
        print(f"JWTError during token verification: {e}")
        return None
    except Exception as e:  # 그 외 예외
        print(f"Unexpected error during token verification: {e}")
        return None


# 비밀번호 검증 함수 (일반적인 사용자명/비밀번호 인증 시 사용)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """일반 텍스트 비밀번호와 해시된 비밀번호를 비교합니다."""
    return pwd_context.verify(plain_password, hashed_password)


# 비밀번호 해시 생성 함수 (일반적인 사용자명/비밀번호 인증 시 사용)
def get_password_hash(password: str) -> str:
    """일반 텍스트 비밀번호의 해시를 생성합니다."""
    return pwd_context.hash(password)
