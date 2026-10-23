"""공통 미들웨어: CORS + 요청 로깅.

요청 로그에는 메서드 · 경로 · 상태 코드 · 처리 시간 · 요청 ID만 남겨요.
쿼리스트링(검색어에 이름 · 연락처가 들어갈 수 있음), 헤더(Authorization 등), 본문(비밀번호)은 남기지 않아요.
"""
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings

logger = logging.getLogger("gourmand.request")

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"
# 프론트가 보낸 요청 ID는 이 형식일 때만 이어 써요 (로그에 아무 문자열이나 들어오지 않게)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def _request_id_of(request: Request) -> str:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    return incoming if REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex[:12]


def _level_of(status: int) -> int:
    if status >= 500:
        return logging.ERROR
    if status >= 400:
        return logging.WARNING
    return logging.INFO


async def log_requests(request: Request, call_next) -> Response:
    # 프론트가 보낸 요청 ID가 있으면 이어 쓰고, 없으면 새로 만들어요 (오류 문의 시 로그 찾기용)
    request_id = _request_id_of(request)
    # 500 오류 handler도 같은 요청 ID를 로그 · 응답 헤더에 쓰도록 저장해요
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("%s %s → 500 %.1fms id=%s", request.method, request.url.path, elapsed_ms, request_id)
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers[PROCESS_TIME_HEADER] = f"{elapsed_ms:.1f}"
    logger.log(
        _level_of(response.status_code),
        "%s %s → %d %.1fms id=%s",
        request.method,
        request.url.path,
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
