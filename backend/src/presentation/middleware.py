"""공통 미들웨어: CORS + 요청 로깅.

요청 로그에는 메서드 · 경로 · 상태 코드 · 처리 시간 · 요청 ID만 남겨요.
헤더(Authorization 등)와 본문은 남기지 않고, 쿼리의 비밀값(password, token 등)은 *** 로 가려요.
"""
import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings

logger = logging.getLogger("gourmand.request")

SENSITIVE_QUERY_KEYS = {"password", "token", "access_token", "refresh_token", "secret", "authorization", "code"}

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"


def _safe_path(request: Request) -> str:
    if not request.query_params:
        return request.url.path
    query = "&".join(
        f"{key}={'***' if key.lower() in SENSITIVE_QUERY_KEYS else value}"
        for key, value in request.query_params.multi_items()
    )
    return f"{request.url.path}?{query}"


def _level_of(status: int) -> int:
    if status >= 500:
        return logging.ERROR
    if status >= 400:
        return logging.WARNING
    return logging.INFO


async def log_requests(request: Request, call_next) -> Response:
    # 프론트가 보낸 요청 ID가 있으면 이어 쓰고, 없으면 새로 만들어요 (오류 문의 시 로그 찾기용)
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("%s %s → 500 %.1fms id=%s", request.method, _safe_path(request), elapsed_ms, request_id)
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers[PROCESS_TIME_HEADER] = f"{elapsed_ms:.1f}"
    logger.log(
        _level_of(response.status_code),
        "%s %s → %d %.1fms id=%s",
        request.method,
        _safe_path(request),
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


def register_middlewares(app: FastAPI) -> None:
    # 나중에 추가한 미들웨어가 바깥쪽이에요. CORS를 가장 바깥에 둬야 preflight(OPTIONS)를 먼저 처리해요
    app.middleware("http")(log_requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, PROCESS_TIME_HEADER],
    )
