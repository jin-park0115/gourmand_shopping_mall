"""SCRUM-30 · 31 후속 (Slack 이슈): 관리자 주문 차단 · 고객에게 운송장 보이기 · 배송지를 계정별로 저장 (테스트 DB).

토큰은 진짜 회원가입 · 로그인을 거쳐서 받아요.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from database import get_session
from infrastructure.auth.models import AddressModel, MemberModel
from infrastructure.auth.security import hash_password
from infrastructure.cart.models import CartItemModel
from infrastructure.order.models import OrderModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123", "address2": "4층"}
ADMIN_BLOCKED = {
    "code": "FORBIDDEN",
    "message": "관리자 계정으로는 장바구니 담기 · 주문을 할 수 없어요. 고객 계정으로 로그인해 주세요.",
}


@pytest.fixture
async def ctx(db_session):
    db_session.add(MemberModel(email="admin@test.com", password_hash=hash_password(PASSWORD), name="관리자", role="admin"))
    lotus = (await make_product(db_session, name="로투스", price=4500, stock=10)).product_id
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "db": db_session, "lotus": lotus}
    app.dependency_overrides.clear()


async def _login(client, email: str, *, signup: bool = True) -> dict:
    if signup:
        await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": email.split("@")[0]})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _order(client, headers: dict, product_id: int, **extra) -> dict:
    await client.post("/cart/items", json={"productId": product_id, "quantity": 1}, headers=headers)
    res = await client.post("/orders", json={**SHIPPING, **extra}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_admin_cannot_add_to_cart_or_order(ctx) -> None:
    client, db = ctx["client"], ctx["db"]
    admin = await _login(client, "admin@test.com", signup=False)

    res = await client.post("/cart/items", json={"productId": ctx["lotus"], "quantity": 1}, headers=admin)
    assert res.status_code == 403 and res.json() == ADMIN_BLOCKED
    res = await client.post("/orders", json=SHIPPING, headers=admin)
    assert res.status_code == 403 and res.json() == ADMIN_BLOCKED

    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(CartItemModel)) == 0
    assert await db.scalar(select(func.count()).select_from(OrderModel)) == 0


async def test_customer_sees_courier_and_tracking_number(ctx) -> None:
    client = ctx["client"]
    kim = await _login(client, "kim@test.com")
    admin = await _login(client, "admin@test.com", signup=False)
    order = await _order(client, kim, ctx["lotus"])
    assert (order["courier"], order["trackingNo"]) == (None, None)  # 출고 전

    oid = order["orderId"]
    await client.patch(f"/admin/orders/{oid}/status", json={"status": "상품준비중"}, headers=admin)
    await client.patch(
        f"/admin/orders/{oid}/status",
        json={"status": "배송중", "courier": "CJ대한통운", "trackingNo": "1234-5678-9012"},
        headers=admin,
    )

    detail = (await client.get(f"/orders/{oid}", headers=kim)).json()
    listed = (await client.get("/orders", headers=kim)).json()["items"][0]
    for body in (detail, listed):
        assert (body["status"], body["courier"], body["trackingNo"]) == ("배송중", "CJ대한통운", "1234-5678-9012")


async def test_saved_address_belongs_to_account(ctx) -> None:
    client, db = ctx["client"], ctx["db"]
    kim, lee = await _login(client, "kim@test.com"), await _login(client, "lee@test.com")

    assert (await client.get("/orders/saved-address", headers=kim)).json() is None
    await _order(client, kim, ctx["lotus"])  # 저장 안 함 (기본)
    assert (await client.get("/orders/saved-address", headers=kim)).json() is None

    await _order(client, kim, ctx["lotus"], saveAddress=True)
    assert (await client.get("/orders/saved-address", headers=kim)).json() == SHIPPING
    assert (await client.get("/orders/saved-address", headers=lee)).json() is None  # 다른 회원에게는 안 보여요

    # 다시 저장하면 덮어써요 (한 줄 유지)
    moved = {**SHIPPING, "address1": "부산 해운대구 우동 1", "address2": None}
    await _order(client, kim, ctx["lotus"], **moved, saveAddress=True)
    assert (await client.get("/orders/saved-address", headers=kim)).json() == moved
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(AddressModel)) == 1


async def test_saved_address_needs_login(ctx) -> None:
    res = await ctx["client"].get("/orders/saved-address")
    assert res.status_code == 401 and res.json()["code"] == "UNAUTHORIZED"


async def test_failed_order_does_not_save_address(ctx) -> None:
    """주문이 실패하면(빈 장바구니) 배송지도 저장되지 않아요 (한 트랜잭션)."""
    client = ctx["client"]
    kim = await _login(client, "kim@test.com")
    res = await client.post("/orders", json={**SHIPPING, "saveAddress": True}, headers=kim)
    assert res.status_code == 409
    assert (await client.get("/orders/saved-address", headers=kim)).json() is None
