"""SCRUM-27: 장바구니 API (담기 · 수량 변경 · 삭제 · 조회, 테스트 DB)."""
import pytest
from httpx import ASGITransport, AsyncClient

from database import get_session
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"


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
    sold_out = await make_product(db_session, name="품절과자", price=1000, stock=0)
    await db_session.flush()
    return cookie.product_id, jelly.product_id, sold_out.product_id


async def _auth(client, email: str = "kim@gourmand.com") -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": "김구르"})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_empty_cart(client) -> None:
    res = await client.get("/cart", headers=await _auth(client))

    assert res.status_code == 200
    assert res.json() == {"items": [], "totalCount": 0, "totalPrice": 0}


async def test_add_returns_whole_cart_in_frontend_shape(client, products) -> None:
    cookie, jelly, _ = products
    headers = await _auth(client)

    await client.post("/cart/items", json={"productId": cookie, "quantity": 2}, headers=headers)
    res = await client.post("/cart/items", json={"productId": jelly}, headers=headers)  # quantity 기본 1

    assert res.status_code == 200
    body = res.json()
    assert [i["id"] for i in body["items"]] == [cookie, jelly]  # 먼저 담은 순
    first = body["items"][0]
    assert first["price"] == 3900  # 할인가
    assert (first["quantity"], first["stock"], first["subtotal"], first["isSoldOut"]) == (2, 5, 7800, False)
    assert {"name", "imageUrl"} <= first.keys()
    assert (body["totalCount"], body["totalPrice"]) == (3, 7800 + 2000)


async def test_adding_same_product_merges_quantity(client, products) -> None:
    cookie, _, _ = products
    headers = await _auth(client)

    await client.post("/cart/items", json={"productId": cookie, "quantity": 2}, headers=headers)
    body = (await client.post("/cart/items", json={"productId": cookie, "quantity": 3}, headers=headers)).json()

    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


async def test_merged_quantity_over_stock_is_409_and_cart_unchanged(client, products) -> None:
    cookie, _, _ = products
    headers = await _auth(client)
    await client.post("/cart/items", json={"productId": cookie, "quantity": 4}, headers=headers)

    res = await client.post("/cart/items", json={"productId": cookie, "quantity": 2}, headers=headers)

    assert res.status_code == 409
    assert res.json()["message"] == "'로투스' 재고가 부족해요. (최대 5개까지 담을 수 있어요)"
    assert (await client.get("/cart", headers=headers)).json()["items"][0]["quantity"] == 4


async def test_sold_out_product_cannot_be_added(client, products) -> None:
    _, _, sold_out = products
    res = await client.post("/cart/items", json={"productId": sold_out}, headers=await _auth(client))

    assert res.status_code == 409
    assert res.json() == {"code": "BUSINESS_RULE_VIOLATION", "message": "'품절과자' 상품이 품절이에요."}


async def test_unknown_product_is_404(client) -> None:
    res = await client.post("/cart/items", json={"productId": 999_999}, headers=await _auth(client))
    assert res.status_code == 404


@pytest.mark.parametrize("quantity", [0, -1, 1000])
async def test_invalid_quantity_is_422(client, products, quantity) -> None:
    cookie, _, _ = products
    res = await client.post("/cart/items", json={"productId": cookie, "quantity": quantity}, headers=await _auth(client))
    assert res.status_code == 422


async def test_set_quantity(client, products) -> None:
    cookie, _, _ = products
    headers = await _auth(client)
    await client.post("/cart/items", json={"productId": cookie}, headers=headers)

    res = await client.patch(f"/cart/items/{cookie}", json={"quantity": 5}, headers=headers)
    assert res.status_code == 200
    assert res.json()["items"][0]["quantity"] == 5

    assert (await client.patch(f"/cart/items/{cookie}", json={"quantity": 6}, headers=headers)).status_code == 409
    assert (await client.patch(f"/cart/items/{cookie}", json={"quantity": 0}, headers=headers)).status_code == 422


async def test_set_quantity_of_product_not_in_cart_is_404(client, products) -> None:
    cookie, _, _ = products
    res = await client.patch(f"/cart/items/{cookie}", json={"quantity": 1}, headers=await _auth(client))

    assert res.status_code == 404
    assert res.json()["message"] == "장바구니에 없는 상품이에요."


async def test_remove_and_clear(client, products) -> None:
    cookie, jelly, _ = products
    headers = await _auth(client)
    for pid in (cookie, jelly):
        await client.post("/cart/items", json={"productId": pid}, headers=headers)

    res = await client.delete(f"/cart/items/{cookie}", headers=headers)
    assert [i["id"] for i in res.json()["items"]] == [jelly]
    assert (await client.delete(f"/cart/items/{cookie}", headers=headers)).status_code == 404

    res = await client.delete("/cart", headers=headers)
    assert res.status_code == 200
    assert res.json()["items"] == []


async def test_carts_are_separated_per_member(client, products) -> None:
    cookie, jelly, _ = products
    kim = await _auth(client, "kim@gourmand.com")
    lee = await _auth(client, "lee@gourmand.com")
    await client.post("/cart/items", json={"productId": cookie}, headers=kim)
    await client.post("/cart/items", json={"productId": jelly}, headers=lee)

    assert [i["id"] for i in (await client.get("/cart", headers=kim)).json()["items"]] == [cookie]
    # 남의 장바구니 상품은 내 장바구니에 없는 상품이라 404 — 지워지지 않아요
    assert (await client.delete(f"/cart/items/{jelly}", headers=kim)).status_code == 404
    assert [i["id"] for i in (await client.get("/cart", headers=lee)).json()["items"]] == [jelly]


async def test_item_shows_sold_out_when_stock_runs_out_after_adding(client, products, db_session) -> None:
    cookie, _, _ = products
    headers = await _auth(client)
    await client.post("/cart/items", json={"productId": cookie}, headers=headers)

    from infrastructure.product.models import ProductModel

    (await db_session.get(ProductModel, cookie)).stock = 0
    await db_session.flush()

    item = (await client.get("/cart", headers=headers)).json()["items"][0]
    assert (item["isSoldOut"], item["stock"]) == (True, 0)


@pytest.mark.parametrize(
    ("method", "url"),
    [("get", "/cart"), ("post", "/cart/items"), ("patch", "/cart/items/1"), ("delete", "/cart/items/1"), ("delete", "/cart")],
)
async def test_cart_requires_login(client, method, url) -> None:
    kwargs = {"json": {"productId": 1, "quantity": 1}} if method in ("post", "patch") else {}
    res = await getattr(client, method)(url, **kwargs)
    assert res.status_code == 401
