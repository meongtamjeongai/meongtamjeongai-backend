# app/crud/crud_phishing.py
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phishing_case import PhishingCase
from app.models.phishing_category import PhishingCategory, PhishingCategoryEnum
from app.schemas.phishing import PhishingCaseCreate, PhishingCaseUpdate


async def get_all_categories(db: AsyncSession) -> List[PhishingCategory]:
    """모든 피싱 유형 목록을 조회합니다."""
    stmt = select(PhishingCategory)
    result = await db.execute(stmt)
    return result.scalars().all()


async def populate_categories(db: AsyncSession):
    """Enum에 정의된 피싱 유형을 DB에 초기 데이터로 삽입합니다."""
    # count()를 위해 동기적인 scalar 쿼리 실행
    count_stmt = select(func.count()).select_from(PhishingCategory)
    category_count = (await db.execute(count_stmt)).scalar_one()

    if category_count == 0:
        for category_enum in PhishingCategoryEnum:
            db_category = PhishingCategory(
                code=category_enum.value,
                description=PhishingCategoryEnum.get_description(category_enum),
            )
            db.add(db_category)
        await db.flush()
        print("Phishing categories have been populated.")


async def get_phishing_case(db: AsyncSession, case_id: int) -> Optional[PhishingCase]:
    """ID로 특정 피싱 사례를 조회합니다."""
    stmt = select(PhishingCase).where(PhishingCase.id == case_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_phishing_cases(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[PhishingCase]:
    """모든 피싱 사례 목록을 페이지네이션하여 조회합니다."""
    stmt = (
        select(PhishingCase).order_by(PhishingCase.id.desc()).offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_phishing_case(
    db: AsyncSession, *, case_in: PhishingCaseCreate
) -> PhishingCase:
    """새로운 피싱 사례를 생성합니다."""
    db_case = PhishingCase(
        title=case_in.title,
        content=case_in.content,
        category_code=case_in.category_code.value,
        case_date=case_in.case_date,
        reference_url=str(case_in.reference_url) if case_in.reference_url else None,
    )
    db.add(db_case)
    await db.flush()
    await db.refresh(db_case)
    return db_case


async def update_phishing_case(
    db: AsyncSession, *, db_case: PhishingCase, case_in: PhishingCaseUpdate
) -> PhishingCase:
    """기존 피싱 사례를 수정합니다."""
    update_data = case_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "reference_url" and value is not None:
            setattr(db_case, field, str(value))
        elif field == "category_code" and value is not None:
            setattr(db_case, field, value.value)
        else:
            setattr(db_case, field, value)
    db.add(db_case)
    await db.flush()
    await db.refresh(db_case)
    return db_case


async def delete_phishing_case(
    db: AsyncSession, *, case_id: int
) -> Optional[PhishingCase]:
    """ID로 특정 피싱 사례를 삭제합니다."""
    db_case = await get_phishing_case(db, case_id=case_id)
    if db_case:
        await db.delete(db_case)
        await db.flush()
    return db_case


async def get_random_phishing_case(
    db: AsyncSession, *, category_code: Optional[PhishingCategoryEnum] = None
) -> Optional[PhishingCase]:
    """특정 카테고리에서 랜덤한 피싱 사례 하나를 조회합니다."""
    stmt = select(PhishingCase)
    if category_code:
        stmt = stmt.where(PhishingCase.category_code == category_code)

    stmt = stmt.order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_category_by_code(
    db: AsyncSession, code: str
) -> Optional[PhishingCategory]:
    """Code로 특정 피싱 카테고리를 조회합니다."""
    stmt = select(PhishingCategory).where(PhishingCategory.code == code)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
