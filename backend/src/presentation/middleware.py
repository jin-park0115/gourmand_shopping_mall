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
from fastapi.responses import JSONResponse

from core.config import get_settings
from presentation.exception_handlers import unhandled_error_handler

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


# NUL 문자(\x00)는 PostgreSQL 글자 칸에 저장할 수 없어서, DB 까지 가면 500 이 나요. 들어오는 곳에서 422 로 막아요
NUL_MESSAGE = "입력에 쓸 수 없는 문자(NUL)가 들어 있어요."


def _has_nul(request: Request, body: bytes) -> bool:
    if "\x00" in request.url.path or b"%00" in request.scope.get("query_string", b""):
        return True
    content_type = request.headers.get("content-type", "")
    markers = [b"\x00"]
    if "json" in content_type:
        markers.append(rb"\u0000")  # JSON 안에서는 \u0000 (6글자)으로 와요
    if "x-www-form-urlencoded" in content_type:
        markers.append(b"%00")  # 로그인 폼은 %00 으로 와요
    return any(m in body for m in markers)


async def reject_nul(request: Request, call_next) -> Response:
    body = await request.body() if request.method in ("POST", "PUT", "PATCH") else b""
    if _has_nul(request, body):
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": NUL_MESSAGE})
    return await call_next(request)


async def log_requests(request: Request, call_next) -> Response:
    # 프론트가 보낸 요청 ID가 있으면 이어 쓰고, 없으면 새로 만들어요 (오류 문의 시 로그 찾기용)
    request_id = _request_id_of(request)
    # 500 오류 handler도 같은 요청 ID를 로그 · 응답 헤더에 쓰도록 저장해요
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # 여기서 500 응답을 만들어야 바깥의 CORS 미들웨어가 헤더를 붙여요.
        # (그냥 raise 하면 CORS 바깥에서 500 이 만들어져서, 브라우저는 '서버에 연결할 수 없어요'로만 봐요)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("%s %s → 500 %.1fms id=%s", request.method, request.url.path, elapsed_ms, request_id)
        return await unhandled_error_handler(request, exc)
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
    # 순서(안 → 밖): reject_nul → log_requests → CORS. 422 · 500 응답에도 요청 로그와 CORS 헤더가 붙어요
    app.middleware("http")(reject_nul)
    app.middleware("http")(log_requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, PROCESS_TIME_HEADER],
    )
