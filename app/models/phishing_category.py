# app/models/phishing_category.py

import enum
from typing import TYPE_CHECKING, List  # 👈 TYPE_CHECKING 임포트

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# 👇 [수정] 순환 참조 방지를 위해 if TYPE_CHECKING 블록 사용
if TYPE_CHECKING:
    from .phishing_case import PhishingCase


class PhishingCategoryEnum(str, enum.Enum):
    GOV_SCAM = "GovScam"
    FRIEND_SCAM = "FriendScam"
    LOAN_SCAM = "LoanScam"
    SMISHING = "Smishing"
    DELIVERY_SCAM = "DeliveryScam"
    SEXTORTION = "Sextortion"
    INVEST_SCAM = "InvestScam"
    NEW_ALERTS = "NewAlerts"

    @classmethod
    def get_description(cls, value: "PhishingCategoryEnum") -> str:
        descriptions = {
            cls.GOV_SCAM: "검찰, 경찰, 금감원 등 공공기관이나 금융기관을 사칭하는 유형",
            cls.FRIEND_SCAM: "가족, 친구, 직장동료 등 지인을 사칭하여 금전을 요구하는 유형",
            cls.LOAN_SCAM: "저금리 대출, 정부 지원 대출 등을 미끼로 접근하는 유형",
            cls.SMISHING: "문자메시지(SMS) 또는 메신저 내 URL 클릭을 유도하거나 악성 앱 설치를 유도하는 유형",
            cls.DELIVERY_SCAM: "택배 배송 조회, 카드 결제 오류, 통관 등을 사칭하는 유형",
            cls.SEXTORTION: "음란 화상 채팅(몸캠) 후 협박하여 금품을 요구하는 유형",
            cls.INVEST_SCAM: "고수익 보장을 미끼로 투자를 유도하는 유형 (주식, 코인, 부동산 등)",
            cls.NEW_ALERTS: "새롭게 등장하거나 기존 수법이 변형되어 주의가 필요한 최신 피싱 및 스캠 수법 또는 관련 주의 환기 뉴스",
        }
        return descriptions.get(value, "알 수 없는 유형")


class PhishingCategory(Base):
    __tablename__ = "phishing_categories"

    code: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationship to PhishingCase
    cases: Mapped[List["PhishingCase"]] = relationship(
        "PhishingCase", back_populates="category"
    )

    def __repr__(self):
        return f"<PhishingCategory(code='{self.code}')>"
