# app/db/session.py
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    # 1. create_async_engine을 사용하여 비동기 엔진 생성
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )

    # 2. async_sessionmaker를 사용하여 비동기 세션 팩토리 생성
    # expire_on_commit=False는 세션이 커밋된 후에도 객체에 접근할 수 있게 해줍니다.
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )

    logger.info(
        f"Async SQLAlchemy engine created for: {str(settings.DATABASE_URL).split('@')[-1] if '@' in str(settings.DATABASE_URL) else str(settings.DATABASE_URL)}"
    )

except Exception as e:
    logger.error(
        f"Error creating async SQLAlchemy engine in session.py: {e}", exc_info=True
    )
    engine = None
    AsyncSessionLocal = None


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입을 위한 비동기 데이터베이스 세션 생성 함수.
    요청 처리 중 세션을 사용하고, 완료 후에는 반드시 닫습니다.
    """
    if not AsyncSessionLocal:
        logger.error("Error in get_async_db: AsyncSessionLocal is not initialized.")
        # 실제 운영에서는 이 시점에 애플리케이션이 시작되지 않아야 하지만,
        # 방어적으로 HTTP 예외를 발생시킬 수 있습니다.
        # 여기서는 로깅만 하고 None을 반환하거나 예외를 발생시킵니다.
        raise RuntimeError("Database session factory is not available.")

    async with AsyncSessionLocal() as session:
        try:
            # 1. API 엔드포인트에 세션(session)을 전달합니다.
            yield session

            # 2. 엔드포인트의 모든 로직이 성공적으로 끝나면, 여기서 한번에 커밋합니다.
            await session.commit()

        except Exception:
            # 3. 엔드포인트 로직 중 어떤 예외라도 발생하면, 여기서 모든 변경사항을 롤백합니다.
            await session.rollback()
            raise
        finally:
            # 4. 성공하든 실패하든, 세션은 항상 안전하게 닫습니다.
            await session.close()
