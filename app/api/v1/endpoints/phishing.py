# app/api/v1/endpoints/phishing.py

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.phishing import PhishingCaseResponse, PhishingCategoryResponse
from app.services.phishing_service import PhishingService

router = APIRouter()


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
