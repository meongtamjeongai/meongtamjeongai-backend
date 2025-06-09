# fastapi_backend/app/schemas/user_point.py
# UserPoint 모델 관련 Pydantic 스키마

from datetime import datetime

from pydantic import Field

from app.schemas.base_schema import BaseModel


class UserPointBase(BaseModel):
    points: int = Field(..., ge=0, description="사용자 보유 포인트 (0 이상)")


# UserPoint 생성은 User 생성 시 자동으로 이루어지므로 별도 Create 스키마는 불필요할 수 있음
# class UserPointCreate(UserPointBase):
#     user_id: int # User 생성 시 함께 생성되므로 직접 요청은 없을 것


class UserPointUpdate(BaseModel):  # 포인트 업데이트 시 사용 (예: 관리자 또는 특정 액션)
    points: int = Field(..., ge=0)


class UserPointResponse(UserPointBase):
    user_id: int  # UserResponse에 포함될 때 식별용
    last_updated_at: datetime

    # Pydantic V2
    model_config = {
        "from_attributes": True,
    }
    # Pydantic V1
    # class Config:
    #     orm_mode = True
