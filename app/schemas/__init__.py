# app/schemas/__init__.py
# Pydantic 스키마 클래스들을 이 파일에서 임포트하여 외부에서 쉽게 접근할 수 있도록 합니다.

from .api_key import (  # 👈 [추가]
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyScope,
    NewApiKeyResponse,
)
from .base_schema import BaseModel
from .conversation import (
    ConversationBase,
    ConversationCreate,
    ConversationLastMessageSummary,
    ConversationResponse,
)
from .gemini import GeminiChatResponse, GeminiProgressCheck
from .message import ChatMessageResponse, MessageBase, MessageCreate, MessageResponse
from .persona import (
    PersonaBase,
    PersonaCreate,
    PersonaCreatorInfo,
    PersonaResponse,
    PersonaUpdate,
)
from .phishing import (
    PhishingCaseCreate,
    PhishingCaseResponse,
    PhishingCaseUpdate,
    PhishingCategoryResponse,
)
from .social_account import (
    SocialAccountBase,
    SocialAccountCreate,
    SocialAccountResponse,
)
from .token import SocialLoginRequest, Token, TokenPayload
from .user import (
    UserBase,
    UserCreate,
    UserDetailResponse,
    UserInDBBase,
    UserResponse,
    UserUpdate,
)
from .user_point import UserPointBase, UserPointResponse, UserPointUpdate

# __all__ 정의 (from app.schemas import * 사용 시 임포트할 대상 명시)
__all__ = [
    "BaseModel",
    "Token",
    "TokenPayload",
    "SocialLoginRequest",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserDetailResponse",
    "UserInDBBase",
    "SocialAccountBase",
    "SocialAccountCreate",
    "SocialAccountResponse",
    "PersonaBase",
    "PersonaCreate",
    "PersonaUpdate",
    "PersonaResponse",
    "PersonaCreatorInfo",
    "ConversationBase",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationLastMessageSummary",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "ChatMessageResponse",
    "UserPointBase",
    "UserPointUpdate",
    "UserPointResponse",
    "GeminiChatResponse",
    "GeminiProgressCheck",
    "PhishingCategoryResponse",
    "PhishingCaseCreate",
    "PhishingCaseUpdate",
    "PhishingCaseResponse",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyScope",
    "NewApiKeyResponse",
]
