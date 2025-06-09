# fastapi_backend/app/core/exceptions.py

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    """
    FastAPI 애플리케이션에 전역 예외 핸들러를 추가합니다.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        의도적으로 발생시킨 HTTPException을 처리합니다.
        - 클라이언트 오류(4xx)는 WARNING 레벨로 로깅합니다.
        """
        logger.warning(
            f"HTTPException caught: Status Code={exc.status_code}, Detail='{exc.detail}', "
            f"Request: {request.method} {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        처리되지 않은 모든 예외(서버 오류)를 처리합니다.
        - 서버 오류(5xx)는 ERROR 레벨로 로깅하며, 전체 트레이스백을 포함합니다.
        - 클라이언트에게는 상세 오류 내용을 노출하지 않습니다.
        """
        logger.error(
            f"Unhandled exception caught: {exc.__class__.__name__}, "
            f"Request: {request.method} {request.url.path}",
            exc_info=True,  # \u003c\u003c\u003c 트레이스백을 로그에 포함시키는 핵심 옵션
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )
