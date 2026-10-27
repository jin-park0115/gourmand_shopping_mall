"""SCRUM-69: 최종 QA 에서 나온 장바구니 · 주문 문제 (테스트 DB).

- 주문하는 사이 다른 탭에서 담은 상품은 장바구니에 남아요 (주문한 상품만 빠져요)
- 주문서 화면이 본 총액(expectedTotalPrice)과 서버 금액이 다르면 409, 아무것도 바뀌지 않아요
동시에 처음 담기(500) 는 한 트랜잭션 안에서는 재현할 수 없어서, 실제 서버에 동시 요청을 보내 확인했어요 (Jira SCRUM-69).
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update

from database import get_session
from domain.order.order import PRICE_CHANGED_MESSAGE
from infrastructure.cart.models import CartItemModel
from infrastructure.order.models import OrderModel
from infrastructure.product.models import ProductModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123"}


@pytest.fixture
async def ctx(db_session):
    lotus = (await make_product(db_session, name="로투스", price=4500, stock=10)).product_id
    jelly = (await make_product(db_session, name="곤약젤리", price=3900, stock=10)).product_id
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/auth/signup", json={"email": "kim@test.com", "password": PASSWORD, "name": "김구르"})
        token = (await client.post("/auth/login", data={"username": "kim@test.com", "password": PASSWORD})).json()["access_token"]
        yield {"client": client, "db": db_session, "kim": {"Authorization": f"Bearer {token}"}, "lotus": lotus, "jelly": jelly}
    app.dependency_overrides.clear()


async def _stock(db, product_id: int) -> int:
    db.expire_all()
    return await db.scalar(select(ProductModel.stock).where(ProductModel.product_id == product_id))


async def test_items_added_during_order_stay_in_cart(ctx, monkeypatch) -> None:
    """주문이 장바구니를 잠근 뒤 다른 탭에서 곤약젤리를 담은 상황: 주문은 로투스만, 곤약젤리는 장바구니에 남아요."""
    client, db, kim, lotus, jelly = ctx["client"], ctx["db"], ctx["kim"], ctx["lotus"], ctx["jelly"]
    await client.post("/cart/items", json={"productId": lotus, "quantity": 2}, headers=kim)
    await client.post("/cart/items", json={"productId": jelly, "quantity": 3}, headers=kim)

    async def locked_before_jelly(self, member_id):  # 잠글 때는 아직 로투스만 있었어요
        return [(lotus, 2)]

    monkeypatch.setattr("infrastructure.cart.repositories.CartRepository.lock_lines", locked_before_jelly)
    res = await client.post("/orders", json=SHIPPING, headers=kim)
    assert res.status_code == 201, res.text
    assert [(i["productId"], i["quantity"]) for i in res.json()["items"]] == [(lotus, 2)]

    cart = (await client.get("/cart", headers=kim)).json()
    assert [(i["id"], i["quantity"]) for i in cart["items"]] == [(jelly, 3)]
    assert (await _stock(db, lotus), await _stock(db, jelly)) == (8, 10)


async def test_order_with_expected_total_matching(ctx) -> None:
    client, kim, lotus = ctx["client"], ctx["kim"], ctx["lotus"]
    await client.post("/cart/items", json={"productId": lotus, "quantity": 2}, headers=kim)
    res = await client.post("/orders", json={**SHIPPING, "expectedTotalPrice": 9000}, headers=kim)
    assert res.status_code == 201 and res.json()["totalPrice"] == 9000


async def test_order_blocked_when_price_changed_after_opening_checkout(ctx) -> None:
    """주문서가 9,000원을 보여 준 뒤 가격이 5,000원으로 올라감: 409, 재고 · 장바구니 그대로, 주문 없음."""
    client, db, kim, lotus = ctx["client"], ctx["db"], ctx["kim"], ctx["lotus"]
    await client.post("/cart/items", json={"productId": lotus, "quantity": 2}, headers=kim)
    shown = (await client.get("/cart", headers=kim)).json()["totalPrice"]
    assert shown == 9000

    await db.execute(update(ProductModel).where(ProductModel.product_id == lotus).values(price=5000))
    await db.commit()

    res = await client.post("/orders", json={**SHIPPING, "expectedTotalPrice": shown}, headers=kim)
    assert res.status_code == 409
    assert res.json() == {"code": "BUSINESS_RULE_VIOLATION", "message": PRICE_CHANGED_MESSAGE}

    assert await _stock(db, lotus) == 10
    assert (await client.get("/cart", headers=kim)).json()["totalPrice"] == 10000  # 장바구니 그대로 (새 가격)
    assert await db.scalar(select(func.count()).select_from(OrderModel)) == 0

    # 바뀐 금액으로 다시 주문하면 돼요
    res = await client.post("/orders", json={**SHIPPING, "expectedTotalPrice": 10000}, headers=kim)
    assert res.status_code == 201


async def test_order_blocked_when_cart_changed_in_other_tab(ctx) -> None:
    """주문서를 연 뒤 다른 탭에서 상품을 더 담음: 화면 총액과 달라서 409."""
    client, db, kim, lotus, jelly = ctx["client"], ctx["db"], ctx["kim"], ctx["lotus"], ctx["jelly"]
    await client.post("/cart/items", json={"productId": lotus, "quantity": 1}, headers=kim)
    shown = (await client.get("/cart", headers=kim)).json()["totalPrice"]
    await client.post("/cart/items", json={"productId": jelly, "quantity": 1}, headers=kim)

    res = await client.post("/orders", json={**SHIPPING, "expectedTotalPrice": shown}, headers=kim)
    assert res.status_code == 409 and res.json()["message"] == PRICE_CHANGED_MESSAGE
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(CartItemModel)) == 2


async def test_expected_total_is_optional_and_not_negative(ctx) -> None:
    client, kim, lotus = ctx["client"], ctx["kim"], ctx["lotus"]
    await client.post("/cart/items", json={"productId": lotus, "quantity": 1}, headers=kim)
    res = await client.post("/orders", json={**SHIPPING, "expectedTotalPrice": -1}, headers=kim)
    assert res.status_code == 422
    assert (await client.post("/orders", json=SHIPPING, headers=kim)).status_code == 201  # 없으면 검사하지 않아요
