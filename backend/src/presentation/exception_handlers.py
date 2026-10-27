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
    TooManyRequestsError,
)

logger = logging.getLogger("gourmand.error")

STATUS_BY_ERROR: dict[type[AppError], int] = {
    InvalidValueError: 422,
    BusinessRuleError: 409,
    ConflictError: 409,
    NotFoundError: 404,
    AuthenticationError: 401,
    PermissionDeniedError: 403,
    TooManyRequestsError: 429,
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


# Pydantic 오류 종류(type) → 우리말. {ge} 같은 자리는 오류의 ctx 값으로 채워요. 없는 종류는 영어 원문 그대로
VALIDATION_MESSAGES = {
    "missing": "꼭 입력해 주세요.",
    "greater_than_equal": "{ge} 이상으로 입력해 주세요.",
    "greater_than": "{gt}보다 크게 입력해 주세요.",
    "less_than_equal": "{le} 이하로 입력해 주세요.",
    "less_than": "{lt}보다 작게 입력해 주세요.",
    "string_too_short": "{min_length}자 이상 입력해 주세요.",
    "string_too_long": "{max_length}자 이하로 입력해 주세요.",
    "too_short": "{min_length}개 이상 보내 주세요.",
    "too_long": "{max_length}개 이하로 보내 주세요.",
    "string_type": "문자로 입력해 주세요.",
    "string_pattern_mismatch": "형식이 올바르지 않아요.",
    "int_parsing": "숫자로 입력해 주세요.",
    "int_type": "숫자로 입력해 주세요.",
    "int_from_float": "정수로 입력해 주세요.",
    "float_parsing": "숫자로 입력해 주세요.",
    "bool_parsing": "true 또는 false 로 보내 주세요.",
    "date_parsing": "날짜 형식(YYYY-MM-DD)으로 입력해 주세요.",
    "date_from_datetime_parsing": "날짜 형식(YYYY-MM-DD)으로 입력해 주세요.",
    "datetime_parsing": "날짜 · 시간 형식이 올바르지 않아요.",
    "enum": "{expected} 중 하나로 보내 주세요.",
    "literal_error": "{expected} 중 하나로 보내 주세요.",
    "list_type": "목록으로 보내 주세요.",
    "model_attributes_type": "요청 본문은 JSON 객체로 보내 주세요.",
    "dict_type": "요청 본문은 JSON 객체로 보내 주세요.",
    "json_invalid": "요청 본문(JSON) 형식이 올바르지 않아요.",
    "extra_forbidden": "받지 않는 항목이에요.",
}


def _validation_message(error: dict) -> str:
    """첫 번째 검증 오류 → 화면에 그대로 보여 줄 한 문장 ("rating: 5 이하로 입력해 주세요.")."""
    kind, msg, ctx = error.get("type"), error.get("msg", ""), error.get("ctx") or {}
    if kind == "value_error":  # 스키마에서 직접 raise ValueError("…") 한 문장 · 이메일 형식
        text = "이메일 형식이 올바르지 않아요." if "email address" in msg else msg.removeprefix("Value error, ")
    elif kind in VALIDATION_MESSAGES:
        values = {k: str(v).replace(" or ", ", ") for k, v in ctx.items()}  # enum: "'a', 'b' or 'c'"
        try:
            text = VALIDATION_MESSAGES[kind].format(**values)
        except KeyError:  # ctx 에 자리 값이 없으면 원문
            text = msg
    else:
        text = msg
    if kind == "json_invalid":  # loc 이 ("body", 글자 위치) 라 필드가 아니에요
        return text
    field = ".".join(str(p) for p in error.get("loc", [])[1:])  # 맨 앞 body · query · path 는 빼요
    return f"{field}: {text}" if field else text


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic 검증 오류도 같은 형식으로 맞추고, 필드별 자세한 내용(영어 원문)은 errors에 담아요
    errors = jsonable_encoder(exc.errors())
    message = _validation_message(errors[0]) if errors else "요청 형식이 올바르지 않아요."
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
