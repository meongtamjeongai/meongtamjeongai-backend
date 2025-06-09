# fastapi_backend/app/schemas/token.py
# JWT 토큰 관련 Pydantic 스키마

from typing import Optional, Union

from pydantic import BaseModel, Field  # BaseModel은 pydantic에서 직접 임포트


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None  # 리프레시 토큰은 선택적으로 포함
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Union[int, str]  # 사용자의 ID (일반적으로 숫자 ID 또는 고유 식별 문자열)
    # exp: Optional[int] = None # 만료 시간 (python-jose가 자동으로 처리하므로 필수는 아님)
    # 추가적인 클레임이 있다면 여기에 정의
    # 예를 들어, is_guest: Optional[bool] = None


# 소셜 로그인 요청 시 클라이언트가 전달하는 토큰
class SocialLoginRequest(BaseModel):
    token: str = Field(
        ..., description="소셜 플랫폼에서 발급받은 인증 토큰 (ID 토큰 또는 액세스 토큰)"
    )
    # provider: Optional[str] = None # Path 파라미터로 provider를 받으므로 본문에는 불필요할 수 있음
