"""도메인 예외 → HTTP 응답 변환.

모든 오류 응답을 {"code": ..., "message": ...} 한 가지 형식으로 맞춰서
프론트가 code로 분기하고 message를 그대로 보여줄 수 있게 해요.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from domain.exceptions import (
    AppError,
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    InvalidValueError,
    NotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger("gourmand.error")

STATUS_BY_ERROR: dict[type[AppError], int] = {
    InvalidValueError: 422,
    BusinessRuleError: 409,
    ConflictError: 409,
    NotFoundError: 404,
    AuthenticationError: 401,
    PermissionDeniedError: 403,
}

# 프레임워크가 내는 기본 영어 문구는 우리말로 바꿔요 (직접 적은 detail 은 그대로)
MESSAGE_BY_DEFAULT_DETAIL = {
    "Not Found": "요청한 주소를 찾을 수 없어요.",
    "Method Not Allowed": "이 주소에서는 지원하지 않는 요청 방식이에요.",
}

CODE_BY_HTTP_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _status_of(exc: AppError) -> int:
    for error_type, status in STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return status
    return 400


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    # 401은 표준에 맞게 어떤 인증 방식을 쓰는지 알려줘요
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(status_code=status, content={"code": code, "message": message, **extra}, headers=headers)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error(_status_of(exc), exc.code, exc.message)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic 검증 오류도 같은 형식으로 맞추고, 필드별 자세한 내용은 errors에 담아요
    errors = jsonable_encoder(exc.errors())
    first = errors[0] if errors else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    message = f"{field}: {first.get('msg')}" if field else "요청 형식이 올바르지 않아요."
    return _error(422, "VALIDATION_ERROR", message, errors=errors)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # 없는 경로(404) · 허용되지 않은 메서드(405) 같은 프레임워크 오류도 같은 형식으로
    code = CODE_BY_HTTP_STATUS.get(exc.status_code, "HTTP_ERROR")
    detail = str(exc.detail)
    response = _error(exc.status_code, code, MESSAGE_BY_DEFAULT_DETAIL.get(detail, detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # 예상하지 못한 오류는 서버 로그에만 자세히 남기고, 응답에는 내부 정보를 싣지 않아요
    # 요청 ID를 응답 헤더로 돌려줘서, 사용자가 알려준 ID로 로그를 찾을 수 있게 해요
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("처리되지 않은 오류: %s %s id=%s", request.method, request.url.path, request_id)
    response = _error(500, "INTERNAL_SERVER_ERROR", "서버에서 오류가 발생했어요. 잠시 후 다시 시도해 주세요.")
    response.headers["X-Request-ID"] = request_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
