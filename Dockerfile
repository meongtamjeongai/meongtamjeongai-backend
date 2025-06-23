# Dockerfile

# =================================
# 1. Builder Stage
# =================================
FROM python:3.13-slim-bookworm AS builder

# ... (builder 스테이지는 변경 없음)
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# =================================
# 2. Final Stage
# =================================
FROM python:3.13-slim-bookworm AS final

# 비-루트 사용자 생성
ARG USERNAME=vscode
ARG USER_UID=1000
# USER_GID를 USER_UID와 동일한 값으로 직접 설정합니다.
ARG USER_GID=1000 

RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME --shell /bin/bash

# 실행에 필요한 최소한의 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    coreutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Builder 스테이지에서 빌드된 파이썬 패키지 복사 및 설치
COPY --from=builder /wheels /wheels
COPY --from=builder /workspace/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Gunicorn 설정 파일을 컨테이너에 복사합니다.
COPY gunicorn.conf.py /workspace/gunicorn.conf.py

# entrypoint 스크립트 복사 및 실행 권한 부여
COPY ./scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 애플리케이션 코드 복사
COPY . .

# 디렉토리 소유권을 비-루트 사용자에게 부여
RUN chown -R $USERNAME:$USER_GID /workspace

USER $USERNAME

EXPOSE 80

# 컨테이너 시작 시 entrypoint.sh를 먼저 실행
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Gunicorn을 사용하여 FastAPI 애플리케이션 실행
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]

# Uvicorn을 직접 실행
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]