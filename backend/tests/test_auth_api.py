"""SCRUM-18: 회원가입 · 로그인 API (테스트 DB, 테스트마다 rollback)."""
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from core.config import get_settings
from database import get_session
from main import app

pytestmark = pytest.mark.anyio

SIGNUP = {"email": "Kim@Gourmand.com", "password": "secret-123", "name": "김구르", "phone": "010-1234-5678"}


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _login(client, email: str, password: str):
    return await client.post("/auth/login", data={"username": email, "password": password})


async def test_signup_returns_member_without_password(client) -> None:
    res = await client.post("/auth/signup", json=SIGNUP)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "kim@gourmand.com"  # 소문자로 저장
    assert (body["name"], body["phone"], body["role"]) == ("김구르", "010-1234-5678", "customer")
    assert "password" not in body and "passwordHash" not in body


async def test_duplicate_email_is_409_even_with_different_case(client) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    res = await client.post("/auth/signup", json={**SIGNUP, "email": "KIM@gourmand.com"})

    assert res.status_code == 409
    assert res.json() == {"code": "CONFLICT", "message": "이미 가입된 이메일이에요."}


@pytest.mark.parametrize(
    "override",
    [{"email": "not-an-email"}, {"password": "short"}, {"password": "x" * 65}, {"name": ""}, {"phone": "abc"}],
)
async def test_invalid_signup_is_422(client, override) -> None:
    res = await client.post("/auth/signup", json={**SIGNUP, **override})

    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


async def test_login_returns_bearer_token_with_claims(client) -> None:
    member_id = (await client.post("/auth/signup", json=SIGNUP)).json()["id"]
    res = await _login(client, "kim@gourmand.com", "secret-123")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_expire_minutes * 60
    settings = get_settings()
    payload = jwt.decode(body["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(member_id)
    assert payload["role"] == "customer"
    assert {"jti", "exp"} <= payload.keys()


async def test_login_email_is_case_insensitive(client) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    assert (await _login(client, " KIM@gourmand.com", "secret-123")).status_code == 200


@pytest.mark.parametrize(("email", "password"), [("kim@gourmand.com", "wrong-pass"), ("nobody@gourmand.com", "secret-123")])
async def test_wrong_password_and_unknown_email_get_same_401(client, email, password) -> None:
    await client.post("/auth/signup", json=SIGNUP)
    res = await _login(client, email, password)

    assert res.status_code == 401
    assert res.json() == {"code": "UNAUTHORIZED", "message": "이메일 또는 비밀번호가 올바르지 않아요."}
    assert res.headers["WWW-Authenticate"] == "Bearer"
