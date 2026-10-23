"""SCRUM-16: 도메인 예외와 프레임워크 오류가 모두 {code, message} 형식으로 응답되는지 검사합니다."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from domain.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    InvalidValueError,
    NotFoundError,
    PermissionDeniedError,
)
from presentation.exception_handlers import register_exception_handlers


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    errors = {
        "invalid": InvalidValueError("수량은 1개 이상이어야 해요."),
        "rule": BusinessRuleError("배송완료된 주문은 취소할 수 없어요."),
        "conflict": ConflictError("이미 가입된 이메일이에요."),
        "missing": NotFoundError("주문을 찾을 수 없어요."),
        "auth": AuthenticationError("로그아웃된 토큰이에요."),
        "forbidden": PermissionDeniedError("관리자만 사용할 수 있어요."),
    }

    @app.get("/raise/{name}")
    async def raise_error(name: str):
        raise errors[name]

    @app.get("/boom")
    async def boom():
        raise RuntimeError("db password=secret")

    @app.post("/reviews")
    async def create_review(body: ReviewIn):
        return body

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("name", "status", "code"),
    [
        ("invalid", 422, "INVALID_VALUE"),
        ("rule", 409, "BUSINESS_RULE_VIOLATION"),
        ("conflict", 409, "CONFLICT"),
        ("missing", 404, "NOT_FOUND"),
        ("auth", 401, "UNAUTHORIZED"),
        ("forbidden", 403, "FORBIDDEN"),
    ],
)
def test_domain_error_maps_to_status_and_code(client: TestClient, name: str, status: int, code: str) -> None:
    res = client.get(f"/raise/{name}")
    assert res.status_code == status
    body = res.json()
    assert body["code"] == code
    assert body["message"]


def test_401_has_www_authenticate_header(client: TestClient) -> None:
    res = client.get("/raise/auth")
    assert res.headers["WWW-Authenticate"] == "Bearer"


def test_validation_error_uses_same_format(client: TestClient) -> None:
    res = client.post("/reviews", json={"rating": 6})
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"].startswith("rating:")
    assert body["errors"][0]["loc"] == ["body", "rating"]


def test_unknown_route_uses_same_format(client: TestClient) -> None:
    res = client.get("/no-such-path")
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_method_not_allowed_uses_same_format(client: TestClient) -> None:
    res = client.delete("/reviews")
    assert res.status_code == 405
    assert res.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "allow" in res.headers


def test_unexpected_error_hides_internal_details(client: TestClient) -> None:
    res = client.get("/boom")
    assert res.status_code == 500
    body = res.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert "secret" not in res.text


def test_main_app_registers_handlers() -> None:
    from main import app

    res = TestClient(app).get("/no-such-path")
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"
