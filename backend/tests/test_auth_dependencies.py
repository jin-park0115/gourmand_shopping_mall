"""SCRUM-19: get_current_user · require_admin · get_optional_user + 로그아웃 블랙리스트 (테스트 DB)."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from core.config import get_settings
from database import get_session
from domain.auth.member import CurrentUser, Member, MemberRole
from infrastructure.auth.models import MemberModel, TokenBlacklistModel
from infrastructure.auth.security import create_access_token
from main import app
from presentation.auth.dependencies import get_current_user, get_optional_user, require_admin
from presentation.exception_handlers import register_exception_handlers

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"

# 의존성만 확인하려고 만든 작은 앱 (실제 라우터는 C · A 가 붙여요)
probe = FastAPI()
register_exception_handlers(probe)


@probe.get("/member-only")
async def member_only(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"memberId": user.member_id, "role": user.role.value}


@probe.get("/admin-only")
async def admin_only(admin: CurrentUser = Depends(require_admin)) -> dict:
    return {"memberId": admin.member_id}


@probe.get("/public")
async def public(user: CurrentUser | None = Depends(get_optional_user)) -> dict:
    return {"memberId": user.member_id if user else None}


@pytest.fixture
async def clients(db_session):
    async def _session():
        yield db_session

    for a in (app, probe):
        a.dependency_overrides[get_session] = _session
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api,
        AsyncClient(transport=ASGITransport(app=probe), base_url="http://test") as p,
    ):
        yield api, p
    for a in (app, probe):
        a.dependency_overrides.clear()


async def _signup_and_login(api, email: str = "kim@gourmand.com") -> tuple[int, str]:
    member_id = (await api.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": "김구르"})).json()["id"]
    token = (await api.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return member_id, token


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_me_returns_my_info(clients) -> None:
    api, _ = clients
    member_id, token = await _signup_and_login(api)

    res = await api.get("/auth/me", headers=_bearer(token))

    assert res.status_code == 200
    assert res.json()["id"] == member_id
    assert res.json()["email"] == "kim@gourmand.com"


async def test_missing_token_is_401_in_our_format(clients) -> None:
    _, probe_client = clients
    res = await probe_client.get("/member-only")

    assert res.status_code == 401
    assert res.json() == {"code": "UNAUTHORIZED", "message": "로그인이 필요해요."}
    assert res.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer not-a-jwt", "Basic abc"])
async def test_bad_token_is_401(clients, header) -> None:
    _, probe_client = clients
    assert (await probe_client.get("/member-only", headers={"Authorization": header})).status_code == 401


async def test_same_token_is_401_after_logout(clients) -> None:
    api, probe_client = clients
    _, token = await _signup_and_login(api)
    assert (await probe_client.get("/member-only", headers=_bearer(token))).status_code == 200

    assert (await api.post("/auth/logout", headers=_bearer(token))).status_code == 204

    res = await probe_client.get("/member-only", headers=_bearer(token))
    assert res.status_code == 401
    assert res.json()["message"] == "로그아웃된 토큰이에요. 다시 로그인해 주세요."
    assert (await api.post("/auth/logout", headers=_bearer(token))).status_code == 401  # 두 번 로그아웃도 401


async def test_logout_keeps_other_tokens_valid(clients) -> None:
    api, probe_client = clients
    _, first = await _signup_and_login(api)
    second = (await api.post("/auth/login", data={"username": "kim@gourmand.com", "password": PASSWORD})).json()["access_token"]

    await api.post("/auth/logout", headers=_bearer(first))

    assert (await probe_client.get("/member-only", headers=_bearer(second))).status_code == 200


async def test_logout_purges_expired_blacklist_rows(clients, db_session) -> None:
    api, _ = clients
    db_session.add(TokenBlacklistModel(jti="old", expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    await db_session.flush()
    _, token = await _signup_and_login(api)

    await api.post("/auth/logout", headers=_bearer(token))

    jtis = (await db_session.scalars(select(TokenBlacklistModel.jti))).all()
    assert "old" not in jtis and len(jtis) == 1


async def test_require_admin_403_for_customer_and_200_for_admin(clients, db_session) -> None:
    api, probe_client = clients
    member_id, token = await _signup_and_login(api)

    res = await probe_client.get("/admin-only", headers=_bearer(token))
    assert res.status_code == 403
    assert res.json() == {"code": "FORBIDDEN", "message": "관리자만 사용할 수 있어요."}

    # role 은 토큰이 아니라 DB 의 현재 값으로 판단해요 → 관리자로 바꾸면 같은 토큰으로 통과
    await db_session.execute(update(MemberModel).where(MemberModel.member_id == member_id).values(role="admin"))
    res = await probe_client.get("/admin-only", headers=_bearer(token))
    assert res.status_code == 200
    assert res.json() == {"memberId": member_id}


async def test_require_admin_without_token_is_401(clients) -> None:
    _, probe_client = clients
    assert (await probe_client.get("/admin-only")).status_code == 401


async def test_token_of_deleted_member_is_401(clients) -> None:
    _, probe_client = clients
    ghost = Member(id=999_999, email="x@x.com", name="x", phone=None, role=MemberRole.ADMIN, password_hash="x")
    token, _ = create_access_token(ghost, get_settings())

    assert (await probe_client.get("/member-only", headers=_bearer(token))).status_code == 401


async def test_optional_user(clients) -> None:
    api, probe_client = clients
    member_id, token = await _signup_and_login(api)

    assert (await probe_client.get("/public")).json() == {"memberId": None}
    assert (await probe_client.get("/public", headers=_bearer(token))).json() == {"memberId": member_id}
    assert (await probe_client.get("/public", headers=_bearer("broken"))).json() == {"memberId": None}

    await api.post("/auth/logout", headers=_bearer(token))
    assert (await probe_client.get("/public", headers=_bearer(token))).json() == {"memberId": None}
