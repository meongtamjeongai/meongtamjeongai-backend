# app/db/session.py
import importlib.util
import logging
from typing import AsyncGenerator

from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# settings.DATABASE_URL을 Pydantic URL 객체에서 문자열로 변환합니다.
database_url_str = settings.DATABASE_URL.get_secret_value()

# SQLAlchemy의 make_url을 사용하여 URL을 안전하게 파싱합니다.
# 이 방법은 URL의 각 구성요소를 분리해주므로, 단순 문자열 치환보다 훨씬 안정적입니다.
url_object: URL = make_url(database_url_str)

# URL이 동기식 PostgreSQL을 가리키는지 확인합니다.
if url_object.drivername == "postgresql":
    # asyncpg 라이브러리가 설치되어 있는지 확인합니다.
    # spec_from_file_location을 사용하여 라이브러리의 존재 유무를 안정적으로 파악합니다.
    asyncpg_spec = importlib.util.find_spec("asyncpg")
    if asyncpg_spec:
        # drivername을 비동기 방식인 'postgresql+asyncpg'로 변경합니다.
        # ._replace()는 새로운 URL 객체를 반환합니다.
        url_object = url_object._replace(drivername="postgresql+asyncpg")
        logger.info("Successfully converted DATABASE_URL for asyncpg.")
    else:
        # asyncpg가 설치되어 있지 않으면 경고 로그를 남깁니다.
        logger.warning(
            "asyncpg is not installed. Using the original synchronous 'postgresql' driver. "
            "For async support, please install it with: pip install asyncpg"
        )

try:
    # 1. create_async_engine을 사용하여 비동기 엔진 생성
    # [수정된 부분]
    # URL 문자열 대신, 파싱 및 수정된 URL '객체'를 직접 전달합니다.
    # 이렇게 하면 비밀번호 등이 마스킹되는 문제를 방지할 수 있습니다.
    engine = create_async_engine(
        url_object,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )

    # 2. async_sessionmaker를 사용하여 비동기 세션 팩토리 생성
    # expire_on_commit=False는 세션이 커밋된 후에도 객체에 접근할 수 있게 해줍니다.
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )

    # 로그 출력 시에는 비밀번호를 제외한 정보를 안전하게 표시합니다.
    logger.info(
        f"Async SQLAlchemy engine created for: {engine.url.render_as_string(hide_password=True)}"
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
            # commit()은 선택사항입니다. get_async_db를 사용하는 쪽에서 commit을 관리할 수도 있습니다.
            # 하지만 이 구조는 'Unit of Work' 패턴을 따르므로 여기서 commit하는 것이 일반적입니다.
            await session.commit()
        except Exception:
            # 3. 엔드포인트 로직 중 어떤 예외라도 발생하면, 여기서 모든 변경사항을 롤백합니다.
            await session.rollback()
            raise
        finally:
            # 4. 성공하든 실패하든, 세션은 항상 안전하게 닫습니다.
            await session.close()
