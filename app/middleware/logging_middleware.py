# fastapi_backend/app/middleware/logging_middleware.py

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        모든 HTTP 요청과 응답을 로깅하는 미들웨어입니다.
        - 요청 시작 시: 클라이언트 IP, HTTP 메서드, 경로를 로깅합니다.
        - 응답 완료 후: 처리 시간과 응답 상태 코드를 로깅합니다.
        """
        client_ip = request.client.host if request.client else "Unknown"

        # 요청 처리 시작
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path} from client {client_ip}")

        # 다음 미들웨어 또는 엔드포인트 호출
        response = await call_next(request)

        # 요청 처리 완료
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request finished: {request.method} {request.url.path} with status {response.status_code} "
            f"in {process_time:.2f}ms"
        )

        return response
