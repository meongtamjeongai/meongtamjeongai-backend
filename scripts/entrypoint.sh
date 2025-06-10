#!/bin/bash
# fastapi_backend/scripts/entrypoint.sh

# set -e: 스크립트 실행 중 오류가 발생하면 즉시 실행을 중단합니다.
# 이것은 예기치 않은 상태로 작업이 계속 진행되는 것을 방지하는 중요한 설정입니다.
set -e

# 현재 실행 환경(dev/prod)을 로그로 남겨, 어떤 모드로 스크립트가 시작되었는지 명확히 합니다.
echo "🚀 Entrypoint script started in [${APP_ENV:-dev}] mode..."

# -----------------------------------------------------------------------------
# 1. Firebase 서비스 계정 키 파일 생성
# -----------------------------------------------------------------------------
# GitHub Actions를 통해 주입된 FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 환경 변수가 있는지 확인합니다.
if [ -n "$FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64" ]; then
    echo "🔑 FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 found. Decoding..."
    
    # 키 파일이 저장될 경로를 FIREBASE_SERVICE_ACCOUNT_KEY_PATH 환경 변수에서 읽어옵니다.
    # 이 경로는 FastAPI의 config.py에서 사용하는 경로와 일치해야 합니다.
    KEY_PATH_DIR=$(dirname "$FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    
    # 혹시 디렉토리가 존재하지 않을 경우를 대비해 생성합니다 (-p 옵션은 상위 디렉토리까지 생성).
    mkdir -p "$KEY_PATH_DIR"
    
    # Base64로 인코딩된 문자열을 디코딩하여 실제 JSON 파일로 저장합니다.
    echo "$FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64" | base64 -d > "$FIREBASE_SERVICE_ACCOUNT_KEY_PATH"
    
    echo "✅ Firebase service account file created at $FIREBASE_SERVICE_ACCOUNT_KEY_PATH"
else
    # 해당 환경 변수가 없을 경우, 경고 메시지를 남기고 다음 단계로 넘어갑니다.
    # 로컬 개발 환경 등에서는 이 변수가 없을 수 있습니다.
    echo "⚠️ FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 not set. Skipping file creation."
fi

# -----------------------------------------------------------------------------
# 2. 데이터베이스 마이그레이션 (Alembic)
# -----------------------------------------------------------------------------
# APP_ENV 환경 변수가 'prod'일 경우에만 DB 마이그레이션을 실행합니다.
# 로컬 개발 환경에서는 수동으로 마이그레이션을 관리하는 것이 더 유연할 수 있습니다.
if [ "$APP_ENV" = "prod" ]; then
    echo "🏃 Running Alembic migrations for production..."
    
    # 마이그레이션 실행 전, 진단을 위해 현재 상태를 로깅합니다.
    # 2>/dev/null 은 혹시 alembic 명령 자체가 실패할 경우 에러 메시지를 숨겨 깔끔한 로그를 유지합니다.
    # || echo 'not available' 은 앞선 명령이 실패했을 때 대신 출력될 기본 메시지입니다.
    echo "--- Alembic Status ---"
    echo "DB current revision: $(alembic current 2>/dev/null || echo 'not available')"
    echo "Code head revision: $(alembic heads 2>/dev/null || echo 'not available')"
    echo "----------------------"

    # alembic upgrade head 명령을 실행하고, 만약 실패하면 (종료 코드가 0이 아니면)
    # 스크립트를 중단하고 명확한 에러 메시지를 남깁니다.
    if ! alembic upgrade head; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!! ❌ CRITICAL: Alembic migration failed."
        echo "!! The application will not start."
        echo "!! Check the logs above for errors like 'Can't locate revision'."
        echo "!! This usually means the DB is at a revision that no longer exists in the codebase."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        # 컨테이너가 실패 상태로 종료되도록 0이 아닌 종료 코드(1)로 스크립트를 중단합니다.
        exit 1
    fi
    
    echo "✅ Alembic migrations completed successfully."
fi

# -----------------------------------------------------------------------------
# 3. 메인 애플리케이션 실행
# -----------------------------------------------------------------------------
# 이 스크립트의 사전 작업이 모두 성공적으로 끝나면,
# Dockerfile의 CMD에서 전달된 원래의 명령어를 실행합니다.
exec "$@"