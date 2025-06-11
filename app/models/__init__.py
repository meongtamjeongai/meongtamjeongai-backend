# fastapi_backend/app/models/__init__.py
# 모델 클래스들을 이 파일에서 임포트하여 외부에서 쉽게 접근할 수 있도록 합니다.

from .base import Base  # Base 클래스 임포트
from .conversation import Conversation
from .message import Message, SenderType
from .persona import Persona
from .phishing_case import PhishingCase
from .phishing_category import PhishingCategory, PhishingCategoryEnum
from .social_account import SocialAccount, SocialProvider
from .user import User
from .user_point import UserPoint

# __all__ 정의 (from app.models import * 사용 시 임포트할 대상 명시)
__all__ = [
    "Base",
    "User",
    "SocialAccount",
    "SocialProvider",  # Enum도 포함
    "Persona",
    "Conversation",
    "Message",
    "SenderType",  # Enum도 포함
    "UserPoint",
    "PhishingCategory",
    "PhishingCategoryEnum",
    "PhishingCase",
]
