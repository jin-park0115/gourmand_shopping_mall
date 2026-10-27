"""잘못된 입력이 500 이 아니라 422 로 막히는지 (테스트하다 발견한 것).

- DB 번호 칸(integer) 보다 큰 번호 · page: 상품 · 리뷰 · 장바구니 · 주문 · 관리자
- NUL 문자(\\x00): 가입 · 로그인 폼 · 검색어 · 리뷰 본문
- 500 응답에도 CORS 헤더, DB 오류 로그에 입력값을 찍지 않기
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from database import engine, get_session
from domain.auth.member import CurrentUser, MemberRole
from main import app
from presentation.auth.dependencies import get_current_user
from presentation.exception_handlers import register_exception_handlers
from presentation.middleware import register_middlewares
from presentation.schemas import MAX_ID

pytestmark = pytest.mark.anyio

TOO_BIG = MAX_ID + 1  # 2,147,483,648
ORIGIN = "http://localhost:3000"


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _login_as(role: MemberRole) -> None:
    user = CurrentUser(member_id=1, email="u@test.com", role=role)

    async def _user():
        return user

    app.dependency_overrides[get_current_user] = _user


def _is_422(res) -> None:
    assert res.status_code == 422, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", f"/products/{TOO_BIG}", None),
        ("GET", "/products/99999999999", None),
        ("GET", f"/products/{TOO_BIG}/reviews", None),
        ("GET", f"/products?page={TOO_BIG}", None),
        ("GET", "/products?page=99999999999999999999", None),
        ("GET", "/products?ids=1,9999999999", None),
        ("GET", f"/products/1/reviews?page={TOO_BIG}", None),
    ],
)
async def test_big_numbers_are_422_for_guests(client, method, path, body) -> None:
    _is_422(await client.request(method, path, json=body))


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", f"/products/{TOO_BIG}/reviews", {"rating": 5, "content": "열 글자가 넘는 리뷰예요."}),
        ("PATCH", f"/reviews/{TOO_BIG}", {"rating": 4}),
        ("DELETE", f"/reviews/{TOO_BIG}", None),
        ("POST", "/cart/items", {"productId": TOO_BIG, "quantity": 1}),
        ("PATCH", f"/cart/items/{TOO_BIG}", {"quantity": 1}),
        ("DELETE", f"/cart/items/{TOO_BIG}", None),
        ("GET", f"/orders/{TOO_BIG}", None),
        ("GET", f"/orders?page={TOO_BIG}", None),
        ("POST", f"/orders/{TOO_BIG}/cancel", None),
    ],
)
async def test_big_numbers_are_422_for_customers(client, method, path, body) -> None:
    _login_as(MemberRole.CUSTOMER)
    _is_422(await client.request(method, path, json=body))


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", f"/admin/orders/{TOO_BIG}", None),
        ("GET", f"/admin/orders?page={TOO_BIG}", None),
        ("PATCH", f"/admin/orders/{TOO_BIG}/status", {"status": "상품준비중"}),
    ],
)
async def test_big_numbers_are_422_for_admin(client, method, path, body) -> None:
    _login_as(MemberRole.ADMIN)
    _is_422(await client.request(method, path, json=body))


async def test_largest_id_still_reaches_service(client) -> None:
    res = await client.get(f"/products/{MAX_ID}")  # 경계값은 막지 않아요 → 없는 상품 404
    assert res.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("POST", "/auth/signup", {"json": {"email": "nul@test.com", "password": "pass\x00word12", "name": "널"}}),
        ("POST", "/auth/signup", {"json": {"email": "nul@test.com", "password": "password12", "name": "a\x00b"}}),
        ("POST", "/auth/login", {"data": {"username": "a\x00@test.com", "password": "x"}}),
        ("GET", "/products?q=%00", {}),
        ("GET", "/products/suggest?q=%E3%84%B1%00", {}),
        ("POST", "/products/1/reviews", {"json": {"rating": 5, "content": "널 문자\x00가 들어간 리뷰예요."}}),
    ],
)
async def test_nul_is_422_with_cors(client, method, path, kwargs) -> None:
    _login_as(MemberRole.CUSTOMER)
    res = await client.request(method, path, headers={"Origin": ORIGIN}, **kwargs)
    _is_422(res)
    assert res.json()["message"] == "입력에 쓸 수 없는 문자(NUL)가 들어 있어요."
    assert res.headers["access-control-allow-origin"] == ORIGIN


async def test_plain_text_like_100_percent_is_not_blocked(client) -> None:
    res = await client.get("/products", params={"q": "100%"})  # %25 로 와요. NUL(%00) 이 아니에요
    assert res.status_code == 200


def test_server_error_has_cors_header() -> None:
    test_app = FastAPI()
    register_middlewares(test_app)
    register_exception_handlers(test_app)

    @test_app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    res = TestClient(test_app, raise_server_exceptions=False).get("/boom", headers={"Origin": ORIGIN})
    assert res.status_code == 500 and res.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert res.headers["access-control-allow-origin"] == ORIGIN  # 화면이 '연결할 수 없어요' 대신 메시지를 볼 수 있어요


def test_db_errors_do_not_include_parameters() -> None:
    # DB 오류 메시지 · 로그에 [parameters: (...)] (비밀번호 해시 · 이메일 · 주소) 가 붙지 않아요
    assert engine.sync_engine.hide_parameters
