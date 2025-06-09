#!/bin/bash
set -e

echo "🚀 Entrypoint script started in [${APP_ENV:-dev}] mode..."

# FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 환경 변수가 설정되어 있을 경우, 파일로 생성
if [ -n "$FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64" ]; then
    echo "🔑 FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 found. Decoding..."
    
    KEY_PATH=$(dirname "$FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    mkdir -p "$KEY_PATH"
    
    echo "$FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64" | base64 -d > "$FIREBASE_SERVICE_ACCOUNT_KEY_PATH"
    
    echo "✅ Firebase service account file created at $FIREBASE_SERVICE_ACCOUNT_KEY_PATH"
else
    echo "⚠️ FIREBASE_SERVICE_ACCOUNT_KEY_JSON_BASE64 not set. Skipping file creation."
fi

# Alembic DB 마이그레이션 실행 (운영 환경에서만)
if [ "$APP_ENV" = "prod" ]; then
    echo "🏃 Running Alembic migrations for production..."
    alembic upgrade head
    echo "✅ Alembic migrations completed."
fi

# 원래의 CMD 실행 (이제 uvicorn ... 명령이 실행됨)
exec "$@"