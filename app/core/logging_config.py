# fastapi_backend/app/core/logging_config.py

import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    애플리케이션의 로깅 시스템을 설정합니다.
    - 로그 레벨: INFO
    - 포맷: [시간] - [로거 이름] - [로그 레벨] - [메시지]
    - 핸들러: 콘솔(stdout) 및 파일(rotating) 핸들러
    """
    # 로그 포맷 정의
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # 기본 로그 레벨 설정

    # 1. 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    
    # 2. 파일 핸들러 설정 (RotatingFileHandler)
    # 로그 파일이 5MB를 초과하면 새 파일 생성, 최대 5개 파일 유지
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)

    # 루트 로거에 핸들러 추가 (중복 추가 방지)
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

    logging.info("✅ Logging configured successfully. Logs will be sent to console and logs/app.log")