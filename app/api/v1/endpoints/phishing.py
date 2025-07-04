# app/api/v1/endpoints/phishing.py
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_async_db
from app.models.user import User as UserModel
from app.schemas.phishing import (
    PhishingCaseResponse,
    PhishingCategoryResponse,
    PhishingImageAnalysisRequest,
    PhishingImageAnalysisResponse,
)
from app.services.phishing_service import PhishingService

router = APIRouter(tags=["피싱 정보 (Phishing Info)"])


async def get_phishing_service(db: AsyncSession = Depends(get_async_db)) -> PhishingService:
    return PhishingService(db)


@router.get(
    "/categories",
    response_model=List[PhishingCategoryResponse],
    summary="피싱 유형 목록 조회",
)
async def read_phishing_categories(service: PhishingService = Depends(get_phishing_service)):
    return await service.get_all_categories()


@router.get(
    "/cases",
    response_model=List[PhishingCaseResponse],
    summary="피싱 사례 목록 조회",
)
async def read_phishing_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    service: PhishingService = Depends(get_phishing_service),
):
    return await service.get_all_cases(skip=skip, limit=limit)


@router.get(
    "/cases/{case_id}",
    response_model=PhishingCaseResponse,
    summary="특정 피싱 사례 상세 조회",
)
async def read_phishing_case_by_id(
    case_id: int, service: PhishingService = Depends(get_phishing_service)
):
    return await service.get_case_by_id(case_id=case_id)


@router.post(
    "/analyze-image",
    response_model=PhishingImageAnalysisResponse,
    summary="이미지 피싱 위험도 분석",
)
async def analyze_image_for_phishing_risk(
    request: PhishingImageAnalysisRequest,
    service: PhishingService = Depends(get_phishing_service),
    current_user: UserModel = Depends(get_current_active_user),
):
    return await service.analyze_phishing_image(request=request)
