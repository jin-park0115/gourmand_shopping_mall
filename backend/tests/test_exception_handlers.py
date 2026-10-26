"""SCRUM-16: 도메인 예외와 프레임워크 오류가 모두 {code, message} 형식으로 응답되는지 검사합니다."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import date
from enum import Enum

from fastapi import Query
from pydantic import BaseModel, EmailStr, Field, model_validator

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


class Sort(str, Enum):
    NEW = "new"
    LOW = "low"


class SignupIn(BaseModel):
    email: EmailStr
    content: str = Field(min_length=10, max_length=20)
    note: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.note == "금지":
            raise ValueError("이 메모는 쓸 수 없어요.")
        return self


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

    @app.post("/signup")
    async def signup(body: SignupIn):
        return body

    @app.get("/items/{item_id}")
    async def items(item_id: int, sort: Sort = Sort.NEW, size: int = Query(10, le=100), since: date | None = None):
        return item_id

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


@pytest.mark.parametrize(
    ("method", "path", "body", "message"),
    [
        ("post", "/reviews", {"rating": 6}, "rating: 5 이하로 입력해 주세요."),
        ("post", "/reviews", {"rating": 0}, "rating: 1 이상으로 입력해 주세요."),
        ("post", "/reviews", {}, "rating: 꼭 입력해 주세요."),
        ("post", "/reviews", {"rating": "abc"}, "rating: 숫자로 입력해 주세요."),
        ("post", "/reviews", [1], "요청 본문은 JSON 객체로 보내 주세요."),
        ("post", "/signup", {"email": "x", "content": "열 글자가 넘는 내용"}, "email: 이메일 형식이 올바르지 않아요."),
        ("post", "/signup", {"email": "a@b.com", "content": "짧아"}, "content: 10자 이상 입력해 주세요."),
        ("post", "/signup", {"email": "a@b.com", "content": "가" * 21}, "content: 20자 이하로 입력해 주세요."),
        ("post", "/signup", {"email": "a@b.com", "content": "열 글자가 넘는 내용", "note": "금지"}, "이 메모는 쓸 수 없어요."),
        ("get", "/items/abc", None, "item_id: 숫자로 입력해 주세요."),
        ("get", "/items/1?sort=abc", None, "sort: 'new', 'low' 중 하나로 보내 주세요."),
        ("get", "/items/1?size=101", None, "size: 100 이하로 입력해 주세요."),
        ("get", "/items/1?since=2026-13-01", None, "since: 날짜 형식(YYYY-MM-DD)으로 입력해 주세요."),
    ],
)
def test_validation_message_is_korean(client: TestClient, method, path, body, message) -> None:
    res = client.request(method.upper(), path, json=body)
    assert res.status_code == 422 and res.json()["message"] == message
    assert res.json()["errors"]  # 필드별 원문은 그대로


def test_broken_json_message(client: TestClient) -> None:
    res = client.post("/reviews", content=b'{"rating": 5,', headers={"Content-Type": "application/json"})
    assert res.status_code == 422 and res.json()["message"] == "요청 본문(JSON) 형식이 올바르지 않아요."


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
