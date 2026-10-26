"""SCRUM-29: 주문 생성 (재고 차감 · 주문 저장 · 결제완료 · 이력 · 장바구니 비우기를 한 트랜잭션으로, 테스트 DB)."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from database import get_session
from domain.order.status import OrderStatus
from infrastructure.admin.repositories import OrderStatusHistoryRepository
from infrastructure.cart.models import CartItemModel
from infrastructure.order.models import OrderModel, PaymentModel
from infrastructure.product.models import ProductModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123", "address2": "4층"}


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def products(db_session):
    cookie = await make_product(db_session, name="로투스", price=4500, stock=5)
    cookie.discount_price = 3900
    jelly = await make_product(db_session, name="하리보", price=2000, stock=10)
    await db_session.flush()
    return cookie.product_id, jelly.product_id


async def _auth(client, email: str = "kim@gourmand.com") -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": "김구르"})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _add(client, headers, product_id: int, quantity: int) -> None:
    res = await client.post("/cart/items", json={"productId": product_id, "quantity": quantity}, headers=headers)
    assert res.status_code == 200, res.text


async def _stock(db_session, product_id: int) -> int:
    return await db_session.scalar(select(ProductModel.stock).where(ProductModel.product_id == product_id))


async def _count(db_session, model) -> int:
    return await db_session.scalar(select(func.count()).select_from(model))


async def test_place_order_does_everything_in_one_go(client, products, db_session) -> None:
    cookie, jelly = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 2)
    await _add(client, headers, jelly, 3)

    res = await client.post("/orders", json=SHIPPING, headers=headers)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "접수"
    assert body["totalPrice"] == 3900 * 2 + 2000 * 3  # 할인가로 계산
    assert [(i["productId"], i["unitPrice"], i["quantity"], i["subtotal"]) for i in body["items"]] == [
        (cookie, 3900, 2, 7800),
        (jelly, 2000, 3, 6000),
    ]
    assert (body["recipient"], body["address2"]) == ("김구르", "4층")
    assert body["payment"]["status"] == "결제완료"
    assert body["payment"]["amount"] == body["totalPrice"]
    assert body["payment"]["paidAt"] is not None

    # 재고 차감 · 장바구니 비우기
    assert (await _stock(db_session, cookie), await _stock(db_session, jelly)) == (3, 7)
    assert await _count(db_session, CartItemModel) == 0
    # 이력 첫 줄: 없음 → 접수 (주문 생성은 changed_by 없음)
    history = await OrderStatusHistoryRepository(db_session).list_by_order(body["orderId"])
    assert [(h.from_status, h.to_status, h.changed_by) for h in history] == [(None, OrderStatus.RECEIVED, None)]
    assert history[0].changed_at == (await db_session.get(OrderModel, body["orderId"])).ordered_at


async def test_unit_price_is_fixed_at_order_time(client, products, db_session) -> None:
    cookie, _ = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 1)
    order_id = (await client.post("/orders", json=SHIPPING, headers=headers)).json()["orderId"]

    (await db_session.get(ProductModel, cookie)).discount_price = 1000  # 주문 뒤 할인가가 바뀌어도
    await db_session.flush()

    item = (await client.get(f"/orders/{order_id}", headers=headers)).json()["items"][0]
    assert item["unitPrice"] == 3900


async def test_not_enough_stock_rolls_back_everything(client, products, db_session) -> None:
    """재고 부족 시 전체 롤백 (Jira 완료 조건): 앞 상품 재고도 그대로, 주문 · 결제 · 이력 없음, 장바구니 그대로."""
    cookie, jelly = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 2)  # 상품 번호가 작아서 먼저 재고를 줄여요
    await _add(client, headers, jelly, 5)
    (await db_session.get(ProductModel, jelly)).stock = 4  # 담아 둔 사이 재고가 줄었어요
    await db_session.commit()  # 실제로는 이미 확정된 변경이라 주문 롤백에 같이 되돌려지면 안 돼요

    res = await client.post("/orders", json=SHIPPING, headers=headers)

    assert res.status_code == 409
    assert res.json() == {"code": "BUSINESS_RULE_VIOLATION", "message": "'하리보' 재고가 부족해요. (남은 수량 4개)"}
    assert (await _stock(db_session, cookie), await _stock(db_session, jelly)) == (5, 4)
    assert (await _count(db_session, OrderModel), await _count(db_session, PaymentModel)) == (0, 0)
    assert await _count(db_session, CartItemModel) == 2
    assert (await client.get("/cart", headers=headers)).json()["totalCount"] == 7


async def test_sold_out_product_rolls_back(client, products, db_session) -> None:
    cookie, _ = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 1)
    (await db_session.get(ProductModel, cookie)).stock = 0
    await db_session.commit()

    res = await client.post("/orders", json=SHIPPING, headers=headers)

    assert res.status_code == 409
    assert res.json()["message"] == "'로투스' 상품이 품절이에요."
    assert await _count(db_session, OrderModel) == 0


async def test_empty_cart_is_409(client) -> None:
    res = await client.post("/orders", json=SHIPPING, headers=await _auth(client))

    assert res.status_code == 409
    assert res.json()["message"] == "장바구니가 비어 있어요."


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"recipient": "  "}, "받는 분 이름을 입력해 주세요."),
        ({"phone": "02-123-4567"}, "휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)"),
        ({"zipcode": "1234"}, "우편번호 5자리를 입력해 주세요."),
        ({"address1": ""}, "주소를 입력해 주세요."),
    ],
)
async def test_invalid_shipping_is_422_and_nothing_changes(client, products, db_session, override, message) -> None:
    cookie, _ = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 1)

    res = await client.post("/orders", json={**SHIPPING, **override}, headers=headers)

    assert res.status_code == 422
    assert res.json() == {"code": "INVALID_VALUE", "message": message}
    assert await _stock(db_session, cookie) == 5
    assert await _count(db_session, CartItemModel) == 1


async def test_blank_address2_is_saved_as_null(client, products) -> None:
    cookie, _ = products
    headers = await _auth(client)
    await _add(client, headers, cookie, 1)

    body = (await client.post("/orders", json={**SHIPPING, "address2": "  "}, headers=headers)).json()
    assert body["address2"] is None


async def test_get_my_order_and_others_are_404(client, products) -> None:
    cookie, _ = products
    kim = await _auth(client, "kim@gourmand.com")
    lee = await _auth(client, "lee@gourmand.com")
    await _add(client, kim, cookie, 1)
    order_id = (await client.post("/orders", json=SHIPPING, headers=kim)).json()["orderId"]

    mine = await client.get(f"/orders/{order_id}", headers=kim)
    assert mine.status_code == 200
    assert mine.json()["orderId"] == order_id

    others = await client.get(f"/orders/{order_id}", headers=lee)
    assert others.status_code == 404
    assert (await client.get("/orders/999999", headers=kim)).status_code == 404


@pytest.mark.parametrize(("method", "url"), [("post", "/orders"), ("get", "/orders/1")])
async def test_orders_require_login(client, method, url) -> None:
    kwargs = {"json": SHIPPING} if method == "post" else {}
    assert (await getattr(client, method)(url, **kwargs)).status_code == 401
