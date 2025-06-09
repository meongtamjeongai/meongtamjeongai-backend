# fastapi_backend/app/api/deps.py
# API 엔드포인트에서 사용될 공통 의존성 함수들

from datetime import datetime, timezone  # datetime, timezone 임포트
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt  # ExpiredSignatureError 임포트
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.token import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/example-token-url-for-swagger"
)


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> UserModel:  # 성공 시 항상 UserModel을 반환하도록 타입 힌트 변경
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
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

    except ExpiredSignatureError:  # 토큰 만료 예외 명시적 처리
        print("deps.get_current_user: ❌ TOKEN EXPIRED. Raising 401.")
        raise credentials_exception
    except JWTError as e:  # 그 외 JWT 관련 오류
        print(f"deps.get_current_user: ❌ JWTError during token decoding: {e}")
        raise credentials_exception
    except (
        ValidationError,
        ValueError,
    ) as e:  # Pydantic 유효성 검사 또는 타입 변환 오류
        print(
            f"deps.get_current_user: ❌ Token payload validation/conversion error: {e}"
        )
        raise credentials_exception
    except Exception as e:  # 그 외 모든 예상치 못한 예외
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
