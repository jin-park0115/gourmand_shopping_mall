"""SCRUM-17: CORS 허용 범위와 요청 로그(처리 시간 포함, 비밀정보 제외)를 검사합니다."""
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from presentation.exception_handlers import register_exception_handlers
from presentation.middleware import register_middlewares

ALLOWED = "http://localhost:3000"


def _app() -> FastAPI:
    app = FastAPI()
    register_middlewares(app)
    register_exception_handlers(app)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.post("/login")
    async def login():
        return {"access_token": "issued-token"}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app())


def test_cors_allows_frontend_origin(client: TestClient) -> None:
    res = client.options(
        "/ping",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "Authorization"},
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == ALLOWED
    assert res.headers["access-control-allow-credentials"] == "true"


def test_cors_blocks_unknown_origin(client: TestClient) -> None:
    res = client.get("/ping", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in res.headers


def test_response_has_request_id_and_process_time(client: TestClient) -> None:
    res = client.get("/ping", headers={"X-Request-ID": "req-123"})
    assert res.headers["X-Request-ID"] == "req-123"
    assert float(res.headers["X-Process-Time-Ms"]) >= 0


def test_request_is_logged_with_status_and_time(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="gourmand.request"):
        client.get("/ping")
    record = next(r for r in caplog.records if r.name == "gourmand.request")
    message = record.getMessage()
    assert "GET /ping → 200" in message
    assert "ms" in message
    assert record.levelno == logging.INFO


def test_client_error_is_logged_as_warning(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="gourmand.request"):
        client.get("/no-such-path")
    record = next(r for r in caplog.records if r.name == "gourmand.request")
    assert "→ 404" in record.getMessage()
    assert record.levelno == logging.WARNING


def test_query_headers_and_body_are_not_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="gourmand.request"):
        client.post(
            "/login?token=abc123&q=김철수 010-1234-5678",
            headers={"Authorization": "Bearer secret-jwt"},
            json={"email": "a@b.com", "password": "pw-1234"},
        )
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "POST /login → 200" in logged
    for secret in ("abc123", "김철수", "010-1234-5678", "secret-jwt", "a@b.com", "pw-1234", "issued-token"):
        assert secret not in logged


def test_malformed_request_id_is_replaced(client: TestClient) -> None:
    res = client.get("/ping", headers={"X-Request-ID": "x" * 65})
    assert res.headers["X-Request-ID"] != "x" * 65
    assert len(res.headers["X-Request-ID"]) == 12


def test_server_error_shares_request_id(caplog: pytest.LogCaptureFixture) -> None:
    app = _app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    with caplog.at_level(logging.INFO):
        res = TestClient(app, raise_server_exceptions=False).get("/boom", headers={"X-Request-ID": "req-500"})
    assert res.status_code == 500
    assert res.headers["X-Request-ID"] == "req-500"
    error = next(r for r in caplog.records if r.name == "gourmand.error")
    assert "id=req-500" in error.getMessage()
    assert error.exc_info is not None


def test_uvicorn_access_log_is_disabled() -> None:
    from core.logging import setup_logging

    setup_logging()
    assert logging.getLogger("uvicorn.access").disabled


def test_main_app_registers_middlewares() -> None:
    from main import app

    res = TestClient(app).get("/health", headers={"Origin": ALLOWED})
    assert res.headers["access-control-allow-origin"] == ALLOWED
    assert "X-Process-Time-Ms" in res.headers
