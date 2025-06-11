# app/schemas/phishing.py (수정)

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from app.models.phishing_category import PhishingCategoryEnum


# --- PhishingCategory 스키마 ---
class PhishingCategoryBase(BaseModel):
    code: PhishingCategoryEnum
    description: str


class PhishingCategoryResponse(PhishingCategoryBase):
    model_config = {"from_attributes": True}


# --- PhishingCase 스키마 ---
class PhishingCaseBase(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    case_date: Optional[date] = None
    # 👇 [수정] 베이스 스키마의 타입도 str로 명확히 함
    reference_url: Optional[str] = Field(None, max_length=2048)


class PhishingCaseCreate(PhishingCaseBase):
    category_code: PhishingCategoryEnum
    # 상속받으므로 별도 정의 불필요


class PhishingCaseUpdate(PhishingCaseBase):
    # 👇 [수정] 부분 업데이트를 위해 모든 필드를 Optional로 변경
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    case_date: Optional[date] = None
    reference_url: Optional[str] = Field(None, max_length=2048)
    category_code: Optional[PhishingCategoryEnum] = None


class PhishingCaseResponse(PhishingCaseBase):
    id: int
    category_code: PhishingCategoryEnum
    # 👇 [수정] 응답 모델에서도 타입을 명시적으로 오버라이드하여 모호함 제거
    reference_url: Optional[str] = None

    model_config = {"from_attributes": True}
