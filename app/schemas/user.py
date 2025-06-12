# fastapi_backend/app/schemas/user.py
# User 모델 관련 Pydantic 스키마

from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field, computed_field  # validator 추가

from app.schemas.base_schema import BaseModel
from app.schemas.social_account import SocialAccountResponse
from app.schemas.user_point import UserPointResponse


# 공유 속성 (모든 User 관련 스키마에서 사용 가능)
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: bool = True  # 기본값을 True로 명시 (DB 모델과 일치)
    is_superuser: bool = False
    is_guest: bool = False
    profile_image_key: Optional[str] = Field(
        None, description="새로 업로드된 프로필 이미지의 S3 Object Key"
    )


# DB에 저장될 때 필요한 속성 (비밀번호 포함)
# 이 스키마는 주로 DB에서 읽어올 때 User 모델 객체로부터 변환하기 위해 사용됩니다.
class UserInDBBase(UserBase):
    id: int
    hashed_password: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    social_accounts: List[SocialAccountResponse] = []  # 관계 필드 로드를 위해 포함
    user_point: Optional[UserPointResponse] = None  # 관계 필드 로드를 위해 포함

    model_config = {
        "from_attributes": True,
    }


class UserDetailResponse(UserInDBBase):
    pass


# 사용자 생성 시 요청 본문에 필요한 속성
class UserCreate(UserBase):
    password: Optional[str] = Field(
        None, min_length=8, description="비밀번호 (직접 가입 시 필요)"
    )
    # is_guest는 UserBase에 이미 있음 (기본값 False)
    # email은 UserBase에서 Optional이므로, 회원가입 유형에 따라 필수 여부 조정 가능


# 사용자 정보 업데이트 시 요청 본문에 필요한 속성 (모든 필드 선택적)
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)  # 새 비밀번호
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    profile_image_key: Optional[str] = Field(
        None, description="새로 업로드된 프로필 이미지의 S3 Object Key"
    )


# API 응답으로 기본적인 사용자 정보를 반환할 때 사용될 스키마 (비밀번호 제외)
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


# 클라이언트에게 전달될 최종 사용자 프로필 정보
class UserClientProfileResponse(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    profile_image_key: Optional[str] = None
    is_guest: bool

    # SQLAlchemy 모델의 관계 속성 ('social_accounts', 'user_point')을 매핑하기 위한 필드.
    # 이 필드들은 from_attributes=True에 의해 채워집니다.
    # computed_field에서 이 필드들을 사용합니다.
    # 최종 JSON 응답에서 이 필드들을 직접 노출하고 싶지 않다면,
    # model_dump(exclude={'mapped_social_accounts', 'mapped_user_point'}) 등을 사용하거나
    # 또는 필드 정의 시 exclude=True를 사용할 수 있지만, computed_field 접근에 문제가 생길 수 있습니다.
    # 여기서는 우선 이 필드들을 그대로 두고, computed_field가 이를 사용하도록 합니다.
    # 실제 응답에 이 필드들이 중복으로 나가지 않도록 하려면, computed_field와 이름이 다른
    # 내부용 필드로 정의하고 alias를 사용하는 것이 좋습니다.
    # 또는, computed_field로 최종 필드만 정의하고, FastAPI가 모델을 반환할 때
    # ORM 객체의 속성에 직접 접근하도록 합니다 (이것이 from_attributes의 기본 동작).

    # **가장 간단한 접근:** from_attributes가 ORM 객체의 속성을 Pydantic 모델의
    # 이름이 같은 필드에 매핑한다고 가정하고, computed_field는 ORM 객체에 직접 접근하지 않고
    # Pydantic 모델 인스턴스(`self`)의 다른 (이미 채워진) 필드나, 또는
    # ORM 객체의 속성을 직접 접근할 수 있도록 Pydantic 모델에 해당 속성들을 정의합니다.

    # SQLAlchemy 모델의 'social_accounts'를 위한 필드 (Pydantic이 채움)
    # UserClientProfileResponse 인스턴스가 생성될 때 current_user.social_accounts 값이 여기에 할당됨.
    social_accounts_data: List[SocialAccountResponse] = Field(
        alias="social_accounts", default_factory=list
    )
    # SQLAlchemy 모델의 'user_point'를 위한 필드 (Pydantic이 채움)
    user_point_data: Optional[UserPointResponse] = Field(
        alias="user_point", default=None
    )

    @computed_field(return_type=Optional[str])  # 반환 타입 명시 권장
    @property
    def login_provider(self) -> Optional[str]:
        # 이제 self.social_accounts_data는 Pydantic 필드이므로 직접 사용
        if self.social_accounts_data and len(self.social_accounts_data) > 0:
            return self.social_accounts_data[0].provider.value
        return None

    @computed_field(return_type=int)  # 반환 타입 명시 권장
    @property
    def points(self) -> int:
        # 이제 self.user_point_data는 Pydantic 필드이므로 직접 사용
        if self.user_point_data:
            return self.user_point_data.points
        return 0

    model_config = {
        "from_attributes": True,  # SQLAlchemy 모델 객체의 속성을 Pydantic 필드로 매핑
        "populate_by_name": True,  # alias ("social_accounts", "user_point")가 동작하도록 함
    }


# 사용자 정보와 함께 소셜 계정, 포인트 정보까지 포함하는 상세 응답 (UserInDBBase와 유사하지만 응답용)
class UserDetailResponse(UserInDBBase):
    # UserInDBBase를 상속받으므로 id, email, username, is_active, is_superuser, is_guest,
    # created_at, updated_at, social_accounts, user_point 필드를 이미 가짐.
    # hashed_password는 제외하고 싶다면 여기서 오버라이드하거나, UserInDBBase에서부터 관리.
    # 여기서는 UserInDBBase에 hashed_password가 있으므로, UserDetailResponse에도 포함됨.
    # 클라이언트에 hashed_password를 보내지 않으려면 별도 스키마 필요 또는 UserInDBBase에서 제외.

    # 이 스키마 대신 UserClientProfileResponse를 사용하는 것이 클라이언트 응답에는 더 적합해 보임.
    # UserDetailResponse는 내부 관리용 또는 매우 상세한 정보가 필요할 때 사용.
    pass
