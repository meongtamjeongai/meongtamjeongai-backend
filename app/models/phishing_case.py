# app/models/phishing_case.py

from datetime import date
from typing import TYPE_CHECKING  # 👈 TYPE_CHECKING 임포트

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# 👇 [수정] 순환 참조 방지를 위해 if TYPE_CHECKING 블록 사용
if TYPE_CHECKING:
    from .phishing_category import PhishingCategory


class PhishingCase(Base):
    __tablename__ = "phishing_cases"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    category_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("phishing_categories.code"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    case_date: Mapped[date] = mapped_column(Date, nullable=True)
    reference_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Relationship to PhishingCategory
    category: Mapped["PhishingCategory"] = relationship(
        "PhishingCategory", back_populates="cases"
    )

    def __repr__(self):
        return f"<PhishingCase(id={self.id}, title='{self.title[:30]}...')>"
