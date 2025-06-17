# app/api/v1/api.py

from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router

# 👇 각 엔드포인트 모듈을 직접 임포트하도록 변경
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.api.v1.endpoints.personas import router as personas_router
from app.api.v1.endpoints.phishing import router as phishing_router
from app.api.v1.endpoints.storage import router as storage_router
from app.api.v1.endpoints.users import router as users_router

api_router_v1 = APIRouter()

api_router_v1.include_router(auth_router, prefix="/auth")
api_router_v1.include_router(personas_router, prefix="/personas")
api_router_v1.include_router(conversations_router, prefix="/conversations")
api_router_v1.include_router(users_router, prefix="/users")
api_router_v1.include_router(admin_router, prefix="/admin")
api_router_v1.include_router(phishing_router, prefix="/phishing")
api_router_v1.include_router(storage_router, prefix="/storage")
