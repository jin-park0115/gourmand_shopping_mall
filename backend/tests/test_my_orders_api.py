"""SCRUM-31: 내 주문 목록(상태 · 기간 필터 · 페이지) · 고객 취소 (테스트 DB)."""
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from database import get_session
from domain.order.status import OrderStatus
from infrastructure.admin.repositories import OrderStatusHistoryRepository
from infrastructure.order.models import OrderModel, PaymentModel
from infrastructure.product.models import ProductModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123"}


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def product(db_session) -> int:
    p = await make_product(db_session, name="로투스", price=4500, stock=50)
    await db_session.flush()
    return p.product_id


async def _auth(client, email: str = "kim@gourmand.com") -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": "김구르"})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _order(client, headers, product_id: int, quantity: int = 1) -> int:
    await client.post("/cart/items", json={"productId": product_id, "quantity": quantity}, headers=headers)
    res = await client.post("/orders", json=SHIPPING, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["orderId"]


async def _set(db_session, order_id: int, **values) -> None:
    row = await db_session.get(OrderModel, order_id)
    for key, value in values.items():
        setattr(row, key, value)
    await db_session.commit()


async def _stock(db_session, product_id: int) -> int:
    return await db_session.scalar(select(ProductModel.stock).where(ProductModel.product_id == product_id))


# ── 목록 ──


async def test_list_only_my_orders_newest_first(client, product) -> None:
    kim = await _auth(client, "kim@gourmand.com")
    lee = await _auth(client, "lee@gourmand.com")
    first = await _order(client, kim, product)
    second = await _order(client, kim, product, 2)
    await _order(client, lee, product)

    body = (await client.get("/orders", headers=kim)).json()

    assert [o["orderId"] for o in body["items"]] == [second, first]
    assert (body["total"], body["page"], body["size"], body["pages"]) == (2, 1, 10, 1)
    assert body["items"][0]["items"][0]["quantity"] == 2
    assert body["items"][0]["payment"]["status"] == "결제완료"


async def test_status_filter(client, product, db_session) -> None:
    headers = await _auth(client)
    received = await _order(client, headers, product)
    shipping = await _order(client, headers, product)
    await _set(db_session, shipping, status=OrderStatus.SHIPPING.value)

    res = await client.get("/orders", params={"status": "배송중"}, headers=headers)
    assert [o["orderId"] for o in res.json()["items"]] == [shipping]
    res = await client.get("/orders", params={"status": "접수"}, headers=headers)
    assert [o["orderId"] for o in res.json()["items"]] == [received]


async def test_period_filter_includes_whole_end_day(client, product, db_session) -> None:
    headers = await _auth(client)
    sept = await _order(client, headers, product)
    oct_first = await _order(client, headers, product)
    oct_last = await _order(client, headers, product)
    await _set(db_session, sept, ordered_at=datetime(2026, 9, 30, 23, 59))
    await _set(db_session, oct_first, ordered_at=datetime(2026, 10, 1, 0, 0))
    await _set(db_session, oct_last, ordered_at=datetime(2026, 10, 31, 23, 59))

    res = await client.get("/orders", params={"from": "2026-10-01", "to": "2026-10-31"}, headers=headers)

    assert [o["orderId"] for o in res.json()["items"]] == [oct_last, oct_first]


async def test_pagination(client, product) -> None:
    headers = await _auth(client)
    ids = [await _order(client, headers, product) for _ in range(5)]

    page2 = (await client.get("/orders", params={"page": 2, "size": 2}, headers=headers)).json()

    assert (page2["total"], page2["pages"]) == (5, 3)
    assert [o["orderId"] for o in page2["items"]] == list(reversed(ids))[2:4]


@pytest.mark.parametrize(
    "params",
    [{"status": "없는상태"}, {"from": "2026-10-31", "to": "2026-10-01"}, {"size": 51}, {"page": 0}, {"from": "10/01"}],
)
async def test_invalid_list_params_are_422(client, params) -> None:
    res = await client.get("/orders", params=params, headers=await _auth(client))
    assert res.status_code == 422


# ── 고객 취소 ──


async def test_cancel_restores_stock_cancels_payment_and_writes_history(client, product, db_session) -> None:
    headers = await _auth(client)
    order_id = await _order(client, headers, product, 3)
    assert await _stock(db_session, product) == 47

    res = await client.post(f"/orders/{order_id}/cancel", headers=headers)

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "주문취소"
    assert res.json()["payment"]["status"] == "결제취소"
    assert await _stock(db_session, product) == 50
    payment = await db_session.scalar(select(PaymentModel.status).where(PaymentModel.order_id == order_id))
    assert payment == "결제취소"
    history = await OrderStatusHistoryRepository(db_session).list_by_order(order_id)
    assert [(h.from_status, h.to_status, h.changed_by) for h in history] == [
        (None, OrderStatus.RECEIVED, None),
        (OrderStatus.RECEIVED, OrderStatus.CANCELLED, None),  # 고객 취소는 바꾼 관리자 없음
    ]


async def test_cancel_while_preparing_is_allowed(client, product, db_session) -> None:
    headers = await _auth(client)
    order_id = await _order(client, headers, product)
    await _set(db_session, order_id, status=OrderStatus.PREPARING.value)

    assert (await client.post(f"/orders/{order_id}/cancel", headers=headers)).status_code == 200


@pytest.mark.parametrize("status", [OrderStatus.SHIPPING, OrderStatus.DELIVERED, OrderStatus.DELAYED, OrderStatus.CANCELLED])
async def test_cannot_cancel_after_shipping_and_nothing_changes(client, product, db_session, status) -> None:
    headers = await _auth(client)
    order_id = await _order(client, headers, product, 2)
    await _set(db_session, order_id, status=status.value)

    res = await client.post(f"/orders/{order_id}/cancel", headers=headers)

    assert res.status_code == 409
    assert res.json()["message"] == f"'{status.value}' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요."
    assert await _stock(db_session, product) == 48  # 재고 그대로
    assert (await db_session.get(OrderModel, order_id)).status == status.value


async def test_cancel_twice_is_409_and_stock_restored_once(client, product, db_session) -> None:
    headers = await _auth(client)
    order_id = await _order(client, headers, product, 2)
    await client.post(f"/orders/{order_id}/cancel", headers=headers)

    assert (await client.post(f"/orders/{order_id}/cancel", headers=headers)).status_code == 409
    assert await _stock(db_session, product) == 50


async def test_cannot_cancel_others_order_403_missing_404(client, product, db_session) -> None:
    kim = await _auth(client, "kim@gourmand.com")
    lee = await _auth(client, "lee@gourmand.com")
    order_id = await _order(client, kim, product)

    res = await client.post(f"/orders/{order_id}/cancel", headers=lee)
    assert res.status_code == 403
    assert res.json() == {"code": "FORBIDDEN", "message": "본인 주문만 볼 수 있어요."}
    assert (await db_session.get(OrderModel, order_id)).status == "접수"
    assert (await client.post("/orders/999999/cancel", headers=kim)).status_code == 404


@pytest.mark.parametrize(("method", "url"), [("get", "/orders"), ("post", "/orders/1/cancel")])
async def test_requires_login(client, method, url) -> None:
    assert (await getattr(client, method)(url)).status_code == 401
