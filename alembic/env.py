# fastapi_backend/alembic/env.py
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 현재 env.py 파일의 위치를 기준으로 프로젝트 루트(fastapi_backend)를 찾습니다.
# env.py -> alembic 폴더 -> fastapi_backend 폴더
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))

# 이제 app.models.base (또는 모든 모델이 정의된 곳)와 app.core.config를 임포트할 수 있어야 합니다.
# FastAPI 앱의 설정 임포트 (DATABASE_URL 등)
from app.core.config import settings

# 모든 SQLAlchemy 모델의 Base 클래스
from app.models.base import Base

# ------------------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# FastAPI 앱의 설정을 사용하여 alembic.ini의 sqlalchemy.url을 설정합니다.
if settings.DATABASE_URL:
    database_url_str = str(settings.DATABASE_URL)

    # 만약 URL이 비동기 드라이버(asyncpg)를 사용하도록 설정되어 있다면,
    # Alembic이 동기적으로 작동할 수 있도록 표준 'postgresql' 드라이버로 변경합니다.
    if database_url_str.startswith("postgresql+asyncpg://"):
        database_url_str = database_url_str.replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )

    config.set_main_option("sqlalchemy.url", database_url_str)
else:
    # DATABASE_URL이 설정되지 않은 경우에 대한 처리
    print(
        "Warning: DATABASE_URL from settings is not available for Alembic. Falling back to alembic.ini or default."
    )
    # 만약 DATABASE_URL이 필수라면 여기서 예외를 발생시킬 수 있습니다.
    # raise ValueError("DATABASE_URL must be set in the environment or .env file for Alembic.")

# FastAPI 애플리케이션의 모델 메타데이터를 target_metadata로 설정합니다.
target_metadata = Base.metadata
# ------------------------------------------------------------

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section, {}
        ),  # alembic.ini의 [alembic] 섹션 설정 사용
        prefix="sqlalchemy.",  # sqlalchemy.url 등의 접두사
        poolclass=pool.NullPool,  # 마이그레이션 시에는 NullPool 사용 권장
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
