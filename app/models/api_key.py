# app/models/api_key.py
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class ApiKey(Base):
    """
    외부 서비스(N8N 등) 인증을 위한 API 키 모델
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    key_prefix: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
        index=True,
        comment="API 키의 앞 8자리 (식별용)",
    )
    hashed_key: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="해싱된 전체 API 키"
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="키를 발급한 슈퍼유저 ID",
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=True, comment="키 용도 설명"
    )

    scopes: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=[], comment="이 키가 접근 가능한 권한 범위 목록"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, comment="키 만료일 (NULL이면 무제한)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="키 활성 상태 (False이면 폐기됨)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, comment="마지막 사용일"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, key_prefix='{self.key_prefix}', user_id={self.user_id})>"
