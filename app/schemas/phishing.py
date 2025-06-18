# app/schemas/phishing.py

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


# --- 이미지 분석 요청 스키마 ---
class PhishingImageAnalysisRequest(BaseModel):
    image_base64: str = Field(..., description="분석할 이미지의 Base64 인코딩된 데이터")


# --- 이미지 분석 응답 스키마 ---
class PhishingImageAnalysisResponse(BaseModel):
    phishing_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="이미지가 피싱일 확률 점수 (0-100)",
    )
    reason: str = Field(
        ...,
        description="피싱 점수를 그렇게 판단한 상세한 이유",
    )
