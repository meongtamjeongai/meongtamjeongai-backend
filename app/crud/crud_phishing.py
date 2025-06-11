# app/crud/crud_phishing.py

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.phishing_case import PhishingCase
from app.models.phishing_category import PhishingCategory, PhishingCategoryEnum
from app.schemas.phishing import PhishingCaseCreate, PhishingCaseUpdate


# --- PhishingCategory CRUD ---
def get_all_categories(db: Session) -> List[PhishingCategory]:
    """모든 피싱 유형 목록을 조회합니다."""
    return db.query(PhishingCategory).all()


def populate_categories(db: Session):
    """Enum에 정의된 피싱 유형을 DB에 초기 데이터로 삽입합니다."""
    if db.query(PhishingCategory).count() == 0:
        for category_enum in PhishingCategoryEnum:
            db_category = PhishingCategory(
                code=category_enum.value,
                description=PhishingCategoryEnum.get_description(category_enum),
            )
            db.add(db_category)
        db.commit()
        print("Phishing categories have been populated.")


# --- PhishingCase CRUD ---
def get_phishing_case(db: Session, case_id: int) -> Optional[PhishingCase]:
    """ID로 특정 피싱 사례를 조회합니다."""
    return db.query(PhishingCase).filter(PhishingCase.id == case_id).first()


def get_all_phishing_cases(
    db: Session, skip: int = 0, limit: int = 100
) -> List[PhishingCase]:
    """모든 피싱 사례 목록을 페이지네이션하여 조회합니다."""
    return (
        db.query(PhishingCase)
        .order_by(PhishingCase.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_phishing_case(db: Session, *, case_in: PhishingCaseCreate) -> PhishingCase:
    """새로운 피싱 사례를 생성합니다."""
    # 👇 [수정] Pydantic 모델을 DB 모델로 변환하기 전에 각 필드의 타입을 명시적으로 변환합니다.
    db_case = PhishingCase(
        title=case_in.title,
        content=case_in.content,
        category_code=case_in.category_code.value,  # Enum을 값(문자열)으로 변환
        case_date=case_in.case_date,  # date 타입은 SQLAlchemy가 처리 가능
        # HttpUrl 객체를 str()을 사용하여 명시적으로 문자열로 변환
        reference_url=str(case_in.reference_url) if case_in.reference_url else None,
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


def update_phishing_case(
    db: Session, *, db_case: PhishingCase, case_in: PhishingCaseUpdate
) -> PhishingCase:
    """기존 피싱 사례를 수정합니다."""
    update_data = case_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        # 👇 [수정] 업데이트 시에도 타입 변환 로직 추가
        if field == "reference_url" and value is not None:
            setattr(db_case, field, str(value))
        elif field == "category_code" and value is not None:
            setattr(db_case, field, value.value)
        else:
            setattr(db_case, field, value)

    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case


def delete_phishing_case(db: Session, *, case_id: int) -> Optional[PhishingCase]:
    """ID로 특정 피싱 사례를 삭제합니다."""
    db_case = db.query(PhishingCase).filter(PhishingCase.id == case_id).first()
    if db_case:
        db.delete(db_case)
        db.commit()
    return db_case


def get_random_phishing_case(
    db: Session, *, category_code: Optional[PhishingCategoryEnum] = None
) -> Optional[PhishingCase]:
    """특정 카테고리(또는 전체)에서 랜덤한 피싱 사례 하나를 조회합니다."""
    query = db.query(PhishingCase)
    if category_code:
        query = query.filter(PhishingCase.category_code == category_code)

    # 랜덤 정렬 후 첫 번째 항목 반환
    return query.order_by(func.random()).first()
