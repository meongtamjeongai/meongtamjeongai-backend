# fastapi_backend/app/db/session.py
# SQLAlchemy 데이터베이스 세션 관리

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Session 타입 힌트용
from fastapi import HTTPException # 의존성 주입 함수에서 사용

from app.core.config import settings # 설정 가져오기

try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True # 연결 유효성 검사
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print(f"SQLAlchemy engine created for: {str(settings.DATABASE_URL).split('@')[-1] if '@' in str(settings.DATABASE_URL) else str(settings.DATABASE_URL)}")
except Exception as e:
    print(f"Error creating SQLAlchemy engine in session.py: {e}")
    engine = None
    SessionLocal = None

def get_db() -> SQLAlchemySession: # 제너레이터 대신 직접 세션 반환 후 close
    """
    FastAPI 의존성 주입을 위한 데이터베이스 세션 생성 함수.
    요청 처리 중 세션을 사용하고, 완료 후에는 반드시 닫아야 합니다.
    """
    if not SessionLocal:
        print("Error in get_db: SessionLocal is not initialized.")
        raise HTTPException(
            status_code=503,
            detail="Database service is not configured or unavailable.",
        )
    
    db = SessionLocal()
    try:
        yield db # FastAPI가 Depends와 함께 사용할 때 제너레이터 형태로 제공
    finally:
        db.close()
        # print("Database session closed.") # 디버깅용 로그