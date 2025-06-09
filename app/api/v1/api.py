# fastapi_backend/app/api/v1/api.py
# API v1의 모든 엔드포인트 라우터를 통합합니다.

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    conversations,
    personas,
    users,
)

api_router_v1 = APIRouter()

api_router_v1.include_router(
    auth.router, prefix="/auth", tags=["인증 (Authentication)"]
)
api_router_v1.include_router(
    personas.router, prefix="/personas", tags=["페르소나 (Personas)"]
)
api_router_v1.include_router(
    conversations.router, prefix="/conversations", tags=["대화방 (Conversations)"]
)

api_router_v1.include_router(users.router, prefix="/users", tags=["사용자 (Users)"])
