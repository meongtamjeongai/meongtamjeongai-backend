# app/models/persona.py

from typing import TYPE_CHECKING, List, Any

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
    from .conversation import Conversation
    from .user import User


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    profile_image_key: Mapped[str] = mapped_column(String(2048), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    starting_message: Mapped[str] = mapped_column(
        Text, nullable=True, comment="페르소나의 첫 시작 메시지"
    )
    conversation_starters: Mapped[List[str]] = mapped_column(
        JSON, nullable=True, comment="대화 시작 선택지 목록 (JSON 배열)"
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    # Relationships (변경 없음)
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_personas", foreign_keys=[created_by_user_id]
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="persona", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Persona(id={self.id}, name='{self.name}')>"
