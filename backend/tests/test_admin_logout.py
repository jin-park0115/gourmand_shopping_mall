"""SCRUM-44: 관리자 주문 API 에서 로그아웃한 토큰을 그대로 다시 쓰면 401 인지 검사합니다.

다른 테스트처럼 로그인을 흉내 내지 않고, 실제 /auth/login · /auth/logout (SCRUM-18 · 19) 을 거쳐요.
테스트 DB 를 쓰고, 테스트마다 rollback 해서 아무것도 남지 않아요.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from database import get_session
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.auth.models import MemberModel
from infrastructure.auth.security import hash_password
from infrastructure.order.models import OrderModel
from main import app
from tests.factories import make_order, make_product

pytestmark = pytest.mark.anyio

ADMIN = {"email": "admin@gourmand.com", "password": "admin-pass-1"}
CUSTOMER = {"email": "customer@gourmand.com", "password": "customer-pass-1"}
LOGGED_OUT = {"code": "UNAUTHORIZED", "message": "로그아웃된 토큰이에요. 다시 로그인해 주세요."}


async def _member(session, email: str, password: str, role: str) -> MemberModel:
    member = MemberModel(email=email, password_hash=hash_password(password), name=role, role=role)
    session.add(member)
    await session.flush()
    return member


@pytest.fixture
async def ctx(db_session):
    admin = await _member(db_session, ADMIN["email"], ADMIN["password"], "admin")
    customer = await _member(db_session, CUSTOMER["email"], CUSTOMER["password"], "customer")
    lotus = await make_product(db_session, name="로투스", price=4500, stock=10)
    order = await make_order(db_session, customer, [(lotus, 2)], status="상품준비중")
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "admin_id": admin.member_id, "order_id": order.order_id}
    app.dependency_overrides.clear()


async def _token(client, account: dict) -> str:
    res = await client.post("/auth/login", data={"username": account["email"], "password": account["password"]})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]  # OAuth2 표준 응답이라 snake_case 예요


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_same_token_is_401_after_logout(ctx) -> None:
    client = ctx["client"]
    token = await _token(client, ADMIN)
    assert (await client.get("/admin/orders", headers=_auth(token))).status_code == 200

    assert (await client.post("/auth/logout", headers=_auth(token))).status_code == 204

    # 목록 · 요약 · 상세 · 상태 변경 모두 같은 토큰이면 401
    for method, path, body in [
        ("GET", "/admin/orders", None),
        ("GET", "/admin/orders/summary", None),
        ("GET", f"/admin/orders/{ctx['order_id']}", None),
        ("PATCH", f"/admin/orders/{ctx['order_id']}/status", {"status": "주문취소", "note": "품절"}),
    ]:
        res = await client.request(method, path, headers=_auth(token), json=body)
        assert res.status_code == 401, (path, res.text)
        assert res.json() == LOGGED_OUT
        assert res.headers["WWW-Authenticate"] == "Bearer"


async def test_rejected_change_after_logout_leaves_order_untouched(ctx, db_session) -> None:
    client = ctx["client"]
    token = await _token(client, ADMIN)
    await client.post("/auth/logout", headers=_auth(token))

    res = await client.patch(
        f"/admin/orders/{ctx['order_id']}/status", headers=_auth(token), json={"status": "주문취소", "note": "품절"}
    )
    assert res.status_code == 401
    db_session.expire_all()
    assert await db_session.scalar(select(OrderModel.status).where(OrderModel.order_id == ctx["order_id"])) == "상품준비중"
    history = await db_session.scalars(
        select(OrderStatusHistoryModel).where(OrderStatusHistoryModel.order_id == ctx["order_id"])
    )
    assert history.all() == []


async def test_logging_in_again_gives_a_working_token(ctx) -> None:
    client = ctx["client"]
    old = await _token(client, ADMIN)
    await client.post("/auth/logout", headers=_auth(old))

    new = await _token(client, ADMIN)
    assert new != old
    assert (await client.get("/admin/orders", headers=_auth(new))).status_code == 200
    assert (await client.get("/admin/orders", headers=_auth(old))).status_code == 401


async def test_logging_out_twice_is_401(ctx) -> None:
    client = ctx["client"]
    token = await _token(client, ADMIN)
    assert (await client.post("/auth/logout", headers=_auth(token))).status_code == 204
    res = await client.post("/auth/logout", headers=_auth(token))
    assert res.status_code == 401 and res.json() == LOGGED_OUT


async def test_no_token_customer_and_demoted_admin(ctx, db_session) -> None:
    client = ctx["client"]
    # 토큰 없음 → 401, 고객 토큰 → 403
    assert (await client.get("/admin/orders")).status_code == 401
    customer = await _token(client, CUSTOMER)
    res = await client.get("/admin/orders", headers=_auth(customer))
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN"

    # 권한은 토큰이 아니라 DB 의 현재 role 로 판단: 관리자에서 고객으로 바뀌면 같은 토큰도 403
    token = await _token(client, ADMIN)
    await db_session.execute(update(MemberModel).where(MemberModel.member_id == ctx["admin_id"]).values(role="customer"))
    await db_session.commit()
    assert (await client.get("/admin/orders", headers=_auth(token))).status_code == 403
