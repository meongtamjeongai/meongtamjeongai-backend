# app/services/phishing_service.py

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_phishing
from app.models.phishing_case import PhishingCase
from app.models.phishing_category import PhishingCategory
from app.schemas.phishing import (
    PhishingCaseCreate,
    PhishingCaseUpdate,
    PhishingImageAnalysisRequest,
    PhishingImageAnalysisResponse,
)
from app.services.gemini_service import GeminiService


class PhishingService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()

    def get_all_categories(self) -> List[PhishingCategory]:
        """모든 피싱 유형 목록을 조회합니다."""
        return crud_phishing.get_all_categories(self.db)

    def get_all_cases(self, skip: int, limit: int) -> List[PhishingCase]:
        """모든 피싱 사례 목록을 조회합니다."""
        return crud_phishing.get_all_phishing_cases(self.db, skip=skip, limit=limit)

    def get_case_by_id(self, case_id: int) -> PhishingCase:
        """ID로 특정 피싱 사례를 조회합니다. 없으면 404 에러를 발생시킵니다."""
        db_case = crud_phishing.get_phishing_case(self.db, case_id=case_id)
        if not db_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Phishing case not found"
            )
        return db_case

    def create_new_case(self, case_in: PhishingCaseCreate) -> PhishingCase:
        """새로운 피싱 사례를 생성합니다."""
        # 추가적인 비즈니스 로직 (예: 중복 검사)이 필요하다면 여기에 구현
        return crud_phishing.create_phishing_case(self.db, case_in=case_in)

    def update_existing_case(
        self, case_id: int, case_in: PhishingCaseUpdate
    ) -> PhishingCase:
        """기존 피싱 사례를 수정합니다."""
        db_case = self.get_case_by_id(case_id)  # get_case_by_id가 404 처리를 해줌
        return crud_phishing.update_phishing_case(
            self.db, db_case=db_case, case_in=case_in
        )

    def delete_case(self, case_id: int) -> PhishingCase:
        """피싱 사례를 삭제합니다."""
        db_case = self.get_case_by_id(case_id)  # get_case_by_id가 404 처리를 해줌
        crud_phishing.delete_phishing_case(self.db, case_id=case_id)
        return db_case

    async def analyze_phishing_image(
        self, request: PhishingImageAnalysisRequest
    ) -> PhishingImageAnalysisResponse:
        """
        Gemini 서비스를 호출하여 이미지의 피싱 위험도를 분석합니다.
        """
        response = await self.gemini_service.analyze_image_for_phishing(
            image_base64=request.image_base64
        )
        return response
