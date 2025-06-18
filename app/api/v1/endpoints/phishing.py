# app/api/v1/endpoints/phishing.py

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.phishing import (
    PhishingCaseResponse,
    PhishingCategoryResponse,
    PhishingImageAnalysisRequest,
    PhishingImageAnalysisResponse,
)
from app.services.phishing_service import PhishingService

router = APIRouter(tags=["피싱 정보 (Phishing Info)"])


def get_phishing_service(db: Session = Depends(get_db)) -> PhishingService:
    return PhishingService(db)


@router.get(
    "/categories",
    response_model=List[PhishingCategoryResponse],
    summary="피싱 유형 목록 조회",
    description="정의된 모든 피싱 유형의 코드와 설명을 조회합니다.",
)
def read_phishing_categories(service: PhishingService = Depends(get_phishing_service)):
    return service.get_all_categories()


@router.get(
    "/cases",
    response_model=List[PhishingCaseResponse],
    summary="피싱 사례 목록 조회",
    description="공개된 피싱 사례 목록을 페이지네이션하여 조회합니다.",
)
def read_phishing_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    service: PhishingService = Depends(get_phishing_service),
):
    return service.get_all_cases(skip=skip, limit=limit)


@router.get(
    "/cases/{case_id}",
    response_model=PhishingCaseResponse,
    summary="특정 피싱 사례 상세 조회",
    description="ID로 특정 피싱 사례의 상세 정보를 조회합니다.",
)
def read_phishing_case_by_id(
    case_id: int, service: PhishingService = Depends(get_phishing_service)
):
    return service.get_case_by_id(case_id=case_id)


@router.post(
    "/analyze-image",
    response_model=PhishingImageAnalysisResponse,
    summary="이미지 피싱 위험도 분석",
    description="Base64로 인코딩된 이미지를 전송받아 피싱 위험도를 분석하고 점수와 이유를 반환합니다.",
)
async def analyze_image_for_phishing_risk(
    request: PhishingImageAnalysisRequest,
    service: PhishingService = Depends(get_phishing_service),
    current_user: UserModel = Depends(get_current_active_user),  # 인증된 사용자만 사용
):
    """
    이미지를 분석하여 피싱 위험도를 평가합니다.

    - **image_base64**: 분석할 이미지를 Base64 문자열로 인코딩하여 전송합니다.
    """
    return await service.analyze_phishing_image(request=request)
