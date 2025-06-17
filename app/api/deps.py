# fastapi_backend/app/api/deps.py
# API 엔드포인트에서 사용될 공통 의존성 함수들

from datetime import datetime, timezone
from typing import Any, Optional

# 👇 추가: 쿼리 파라미터를 위한 Query 클래스
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.token import TokenPayload

# tokenUrl을 새로 만든 ID/Password 로그인 엔드포인트 경로로 변경합니다.
# 이렇게 하면 Swagger UI의 'Authorize' 버튼을 눌렀을 때 ID/PW 입력 창이 뜨고,
# 성공 시 자동으로 API 요청 헤더에 토큰이 포함됩니다.
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/password"
)


# 소스에서 토큰을 가져오는 의존성 함수
async def get_token_from_various_sources(
    # 1. 표준 OAuth2 방식 (Authorization: Bearer ... 헤더)
    token_from_header: Optional[str] = Depends(reusable_oauth2),
    # 2. 쿼리 파라미터 방식 (?token=...)
    token_from_query: Optional[str] = Query(
        None, description="인증을 위한 JWT Access Token"
    ),
) -> str:
    """
    여러 소스에서 JWT 토큰을 가져옵니다.
    우선순위: Authorization 헤더 > 'token' 쿼리 파라미터
    토큰이 없으면 401 에러를 발생시킵니다.
    """
    if token_from_header:
        return token_from_header
    if token_from_query:
        return token_from_query

    # 두 방법 모두 토큰이 없는 경우
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_token_from_various_sources),  # 새로운 방식
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        # get_token_from_various_sources 에서 이미 처리하지만, 방어적으로 코드 유지
        raise credentials_exception

    try:
        # 디버깅을 위해, 검증 없이 먼저 페이로드를 디코딩하여 만료 시간 확인
        try:
            unverified_payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
            exp_timestamp = unverified_payload.get("exp")
            exp_datetime = (
                datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                if exp_timestamp
                else "N/A"
            )
            now_utc = datetime.now(timezone.utc)
            print(
                f"deps.get_current_user: ➡️ Token received. Exp: {exp_datetime} | Now: {now_utc}"
            )
        except Exception:
            print(
                "deps.get_current_user: ➡️ Token received (could not pre-decode for logging)."
            )

        # 실제 토큰 검증 (서명, 만료 시간 등)
        payload_dict = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        print(
            f"deps.get_current_user: ✅ Token validation successful. Payload: {payload_dict}"
        )

        user_id_from_payload: Optional[Any] = payload_dict.get("sub")
        if user_id_from_payload is None:
            print("deps.get_current_user: ❌ Token payload missing 'sub' (user_id).")
            raise credentials_exception

        token_data = TokenPayload(sub=str(user_id_from_payload))
        user_id = int(token_data.sub)

    except ExpiredSignatureError:
        print("deps.get_current_user: ❌ TOKEN EXPIRED. Raising 401.")
        raise credentials_exception
    except JWTError as e:
        print(f"deps.get_current_user: ❌ JWTError during token decoding: {e}")
        raise credentials_exception
    except (
        ValidationError,
        ValueError,
    ) as e:
        print(
            f"deps.get_current_user: ❌ Token payload validation/conversion error: {e}"
        )
        raise credentials_exception
    except Exception as e:
        print(
            f"deps.get_current_user: ❌ Unexpected error during token processing: {e}"
        )
        raise credentials_exception

    user = crud_user.get_user(db, user_id=user_id)
    if user is None:
        print(f"deps.get_current_user: ❌ User with ID {user_id} not found in DB.")
        raise credentials_exception

    print(f"deps.get_current_user: ✅ User {user.id} ({user.email}) found.")
    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    if not crud_user.is_active(current_user):
        print(f"deps.get_current_active_user: ❌ User {current_user.id} is inactive.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    print(f"deps.get_current_active_user: ✅ User {current_user.id} is active.")
    return current_user


async def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserModel:
    if not crud_user.is_superuser(current_user):
        print(
            f"deps.get_current_active_superuser: ❌ User {current_user.id} is not a superuser."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    print(
        f"deps.get_current_active_superuser: ✅ User {current_user.id} is a superuser."
    )
    return current_user
