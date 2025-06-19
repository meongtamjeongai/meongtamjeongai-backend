# app/models/user.py

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .api_key import ApiKey
    from .conversation import Conversation
    from .persona import Persona
    from .social_account import SocialAccount
    from .user_point import UserPoint


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(
        String(100), index=True, nullable=True, unique=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
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
    is_guest: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)

    profile_image_key: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Relationships
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    social_accounts: Mapped[List["SocialAccount"]] = relationship(
        "SocialAccount", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    created_personas: Mapped[List["Persona"]] = relationship(
        "Persona",
        back_populates="creator",
        foreign_keys="[Persona.created_by_user_id]",
        cascade="all, delete-orphan",
    )
    user_point: Mapped["UserPoint"] = relationship(
        "UserPoint", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"
