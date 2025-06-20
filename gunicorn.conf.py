# gunicorn.conf.py
# Gunicorn 설정 파일

import os

# 1. 소켓 바인딩
# Docker 환경에서는 컨테이너 외부에서 접근할 수 있도록 0.0.0.0에 바인딩합니다.
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:80")

# 2. 워커(Worker) 프로세스 설정
# 워커 클래스는 Uvicorn의 고성능 비동기 워커를 사용합니다.
worker_class = "uvicorn.workers.UvicornWorker"

# 워커 수는 (2 * CPU 코어 수) + 1 공식을 따릅니다.
# t2.micro (vCPU 1개) 환경을 고려하여 메모리 여유를 위해 2개로 설정
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))

# 비동기 워커를 사용하므로 스레드는 1로 고정합니다.
threads = int(os.environ.get("GUNICORN_THREADS", "1"))

# 3. 타임아웃 설정
# 워커가 지정된 시간 동안 응답이 없으면 재시작합니다.
# Gemini API 호출 등 긴 I/O 작업을 고려하여 넉넉하게 120초로 설정합니다.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

# 4. 로깅 설정
# Gunicorn의 액세스 로그와 에러 로그를 표준 출력(stdout/stderr)으로 보냅니다.
# 이렇게 하면 Docker 컨테이너의 로그로 수집되어 관리가 용이합니다.
accesslog = "-"  # 표준 출력으로 액세스 로그 전송
errorlog = "-"  # 표준 출력으로 에러 로그 전송

# 로그 레벨 설정 (info, debug, warning, error, critical)
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")

# 5. 프로세스 이름 설정
# ps, htop 등에서 프로세스를 쉽게 식별할 수 있도록 이름을 지정합니다.
proc_name = "meongtamjeong-backend"

# 6. 서버 재시작 설정 (운영 환경에서는 비활성화 권장)
# 코드가 변경될 때마다 서버를 자동으로 재시작하는 기능입니다.
# 개발 환경에서는 매우 유용하지만, 운영 환경에서는 안정성을 위해 False로 설정합니다.
# APP_ENV 환경 변수를 확인하여 'dev'일 때만 True로 설정합니다.
reload = os.environ.get("APP_ENV") == "dev"
if reload:
    # reload 시 감시할 디렉토리를 지정할 수 있습니다.
    reload_engine = "auto"
    # reload_extra_files = ["app/"] # 필요시 특정 파일이나 디렉토리 추가


def on_starting(server):
    """
    마스터 프로세스가 시작될 때 딱 한 번 실행됩니다.
    """
    print("🚀 Gunicorn Master Process is starting... This should appear only once.")
    # 예: DB 스키마 존재 여부 확인, 초기 디렉토리 생성 등


def when_ready(server):
    """
    모든 워커가 준비되었을 때 딱 한 번 실행됩니다.
    """
    print("✅ All workers are ready! Server is ready to accept requests.")


def post_fork(server, worker):
    """
    각 워커 프로세스가 생성된 후 실행됩니다. (lifespan과 유사)
    """
    # worker.log.info(f"Worker with pid {worker.pid} has been forked.")
    pass  # FastAPI의 lifespan이 이 역할을 하므로 보통 비워둡니다.
