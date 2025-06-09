# fastapi_backend/alembic/env.py
# FastAPI 애플리케이션의 모델 메타데이터를 가져오기 위한 설정
# ------------------------------------------------------------
# 프로젝트의 루트 경로를 sys.path에 추가하여 app 모듈을 임포트할 수 있도록 합니다.
# 이 경로는 alembic 명령이 실행되는 위치에 따라 조정될 수 있습니다.
# 현재 alembic init alembic으로 생성했고, alembic 명령은 fastapi_backend 폴더에서 실행한다고 가정합니다.
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
from app.core.config import settings  # FastAPI 앱의 설정 임포트 (DATABASE_URL 등)
from app.models.base import (
    Base,  # 모든 SQLAlchemy 모델의 Base 클래스 (아직 생성 전, 곧 생성 예정)
)

# ------------------------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- SQLAlchemy URL 설정 수정 ---
# alembic.ini의 sqlalchemy.url 대신, FastAPI 앱의 설정을 사용하도록 변경합니다.
# 이렇게 하면 환경 변수를 통해 동적으로 DB URL을 관리할 수 있습니다.
# config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
# 또는, Docker 환경에서는 alembic.ini에 직접 명시된 URL을 사용해도 무방합니다.
# 여기서는 alembic.ini에 명시된 값을 우선 사용하고, 필요시 아래 주석을 해제하여 settings.DATABASE_URL을 사용합니다.
# 만약 settings.DATABASE_URL을 사용하려면, 이 파일 상단에서 from app.core.config import settings 임포트가 필요합니다.
# 현재는 settings.DATABASE_URL을 사용하도록 설정합니다.
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))
else:
    # DATABASE_URL이 설정되지 않은 경우에 대한 처리 (예: 기본값 사용 또는 오류 발생)
    # 여기서는 alembic.ini에 설정된 값을 그대로 사용하도록 둡니다. (또는 오류 발생)
    print(
        "Warning: DATABASE_URL from settings is not available for Alembic. Falling back to alembic.ini or default."
    )
    # 만약 DATABASE_URL이 필수라면 여기서 예외를 발생시킬 수 있습니다.
    # raise ValueError("DATABASE_URL must be set in the environment or .env file for Alembic.")

# FastAPI 애플리케이션의 모델 메타데이터를 target_metadata로 설정합니다.
# 이를 통해 Alembic이 자동 생성(autogenerate) 기능을 사용할 때 모델 변경 사항을 감지할 수 있습니다.
# target_metadata = None # 기본값
target_metadata = Base.metadata  # <--- 이 부분을 수정합니다. (Base는 모든 모델의 부모)
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
    # connectable = engine_from_config(  # 기본 생성된 코드
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # --- connectable 수정 ---
    # FastAPI 애플리케이션에서 사용하는 SQLAlchemy 엔진을 공유하거나,
    # 동일한 설정으로 새 엔진을 생성할 수 있습니다.
    # 여기서는 FastAPI 앱의 설정을 사용하여 새 엔진을 만듭니다.
    # 또는 app.db.session.engine (app_engine으로 임포트)을 직접 사용할 수도 있습니다.
    # 단, app_engine이 None일 경우를 대비해야 합니다.

    # 방법 1: FastAPI 앱의 엔진 직접 사용 (app_engine이 None이 아닐 경우)
    # if app_engine:
    #     connectable = app_engine
    # else:
    #     # app_engine이 None이면, 설정에서 URL을 가져와 새로 생성
    #     db_url = settings.DATABASE_URL
    #     if not db_url:
    #         raise ValueError("DATABASE_URL is not configured for online migration.")
    #     connectable = create_engine(db_url) # create_engine 임포트 필요 from sqlalchemy import create_engine

    # 방법 2: config에서 URL을 가져와 항상 새 엔진 생성 (Alembic 표준 방식에 가까움)
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section, {}
        ),  # alembic.ini의 [alembic] 섹션 설정 사용
        prefix="sqlalchemy.",  # sqlalchemy.url 등의 접두사
        poolclass=pool.NullPool,  # 마이그레이션 시에는 NullPool 사용 권장
        # future=True # SQLAlchemy 2.0 스타일 사용 시 (선택적)
    )
    # -------------------------

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
