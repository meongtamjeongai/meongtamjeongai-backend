# fastapi_backend/app/main.py

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import firebase_admin
from fastapi import Depends, FastAPI, HTTPException
from firebase_admin import credentials
from sqlalchemy import text
from sqlalchemy.orm import Session as SQLAlchemySession

from app.api.v1.api import api_router_v1
from app.core.config import settings
from app.core.exceptions import add_exception_handlers
from app.core.logging_config import setup_logging
from app.crud import crud_phishing
from app.db.session import SessionLocal, get_db
from app.db.session import engine as db_engine
from app.middleware.logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 애플리케이션의 생명주기(lifespan) 이벤트 핸들러입니다.
    애플리케이션 시작 시 로깅 설정, DB 연결, Firebase Admin SDK 초기화를 수행합니다.
    """
    # 1. 로그 디렉토리 생성
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # 2. 로깅 설정 (가장 먼저 호출)
    setup_logging()

    # 로거 가져오기 (lifespan 내에서 로그를 남기기 위해)
    logger = logging.getLogger(__name__)

    logger.info(f"--- Application starting in [{settings.APP_ENV}] mode ---")

    # --- 중요 설정값 로그 출력 추가 ---
    logger.info("--- Application Settings ---")
    logger.info(f"Project Name: {settings.PROJECT_NAME}")
    logger.info(f"Access Token Expire Minutes: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    logger.info(f"Refresh Token Expire Days: {settings.REFRESH_TOKEN_EXPIRE_DAYS}")
    logger.info("--------------------------")

    # Firebase Admin SDK 초기화
    firebase_key_path = settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH
    if os.path.exists(firebase_key_path):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_key_path)
                firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase Admin SDK initialized successfully.")
            else:
                logger.info("✅ Firebase Admin SDK already initialized.")
        except Exception as e:
            logger.error(
                f"❌ Error initializing Firebase Admin SDK from path '{firebase_key_path}': {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            f"⚠️ Firebase service account key not found at '{firebase_key_path}'. "
            "Skipping Firebase Admin SDK initialization. This is expected in some test environments."
        )
    # 데이터베이스 연결 테스트 및 초기 데이터 삽입
    if db_engine:
        try:
            with SessionLocal() as db:
                # DB 연결 테스트
                db.execute(text("SELECT 1"))
                logger.info("✅ Database connection test successful on startup.")

                # 👇 [신규] 피싱 카테고리 초기 데이터 삽입
                crud_phishing.populate_categories(db)

        except Exception as e:
            logger.error(
                f"❌ Database connection or initial data population failed on startup: {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            "⚠️ Database engine is not configured. Skipping connection check."
        )

    yield  # 애플리케이션 실행

    # 애플리케이션 종료 시
    logger.info("\n--- FastAPI Application Shutdown ---")
    if db_engine:
        logger.info("Closing database connection pool...")
        await db_engine.dispose()
    logger.info("Application shutdown complete.")


# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Flutter와 FastAPI 기반 Gemini AI 채팅 앱 '멍탐정'의 백엔드 API입니다.",
    version="0.1.0",
    lifespan=lifespan,
)

# --- 미들웨어 및 예외 핸들러 등록 ---
app.add_middleware(LoggingMiddleware)
add_exception_handlers(app)

# API V1 라우터 등록
app.include_router(api_router_v1, prefix=settings.API_V1_STR)


@app.get("/", tags=["기본"])
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}! 🎉"}


@app.get("/db-status", tags=["데이터베이스"])
async def get_db_status(db: SQLAlchemySession = Depends(get_db)):
    try:
        result = db.execute(text("SELECT version()")).scalar_one_or_none()
        if result:
            return {
                "status": "success",
                "message": "Database connection is healthy.",
                "db_version": result,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve DB version."
            )
    except Exception as e:
        # 로깅 시스템이 전역 예외 핸들러에서 처리하므로 여기서는 로깅 불필요
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
