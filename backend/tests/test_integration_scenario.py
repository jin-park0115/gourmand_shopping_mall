"""SCRUM-46: 통합 시나리오 (회원가입 → 담기 → 주문 → 관리자 배송 → 고객 취소 시도 차단, 테스트 DB).

UC A · B · C 를 한 흐름으로 이어서 실제 API 만 거쳐요 (로그인 · 권한 의존성을 바꾸지 않아요).
단계마다 응답과 DB(재고 · 장바구니 · 결제 · 상태 이력)를 다시 조회해서 확인해요.
마지막에 관련 기존 기능(검색 · 필터 · 없는 상품 404)이 그대로인지도 봐요.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from database import get_session
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.auth.models import MemberModel
from infrastructure.auth.security import hash_password
from infrastructure.cart.models import CartItemModel
from infrastructure.order.models import OrderModel, PaymentModel
from infrastructure.product.models import ProductModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

ADMIN = {"email": "admin@gourmand.com", "password": "admin-pass-1"}
CUSTOMER = {"email": "kim@test.com", "password": "secret-123", "name": "김구르", "phone": "010-1234-5678"}
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123", "address2": "4층"}
SHIPPED_CANCEL = "'배송중' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요."


@pytest.fixture
async def ctx(db_session):
    admin = MemberModel(email=ADMIN["email"], password_hash=hash_password(ADMIN["password"]), name="관리자", role="admin")
    db_session.add(admin)
    lotus = await make_product(db_session, name="로투스 비스코프", price=4500, stock=10)
    jelly = await make_product(db_session, name="곤약젤리", price=3900, stock=5)
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "db": db_session, "admin_id": admin.member_id, "lotus": lotus.product_id, "jelly": jelly.product_id}
    app.dependency_overrides.clear()


async def _login(client, email: str, password: str) -> dict:
    res = await client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _stock(db, product_id: int) -> int:
    db.expire_all()
    return await db.scalar(select(ProductModel.stock).where(ProductModel.product_id == product_id))


async def _history(db, order_id: int) -> list[tuple]:
    rows = await db.execute(
        select(OrderStatusHistoryModel.from_status, OrderStatusHistoryModel.to_status, OrderStatusHistoryModel.changed_by)
        .where(OrderStatusHistoryModel.order_id == order_id)
        .order_by(OrderStatusHistoryModel.history_id)
    )
    return [tuple(r) for r in rows]


async def test_signup_to_admin_shipping_then_customer_cancel_is_blocked(ctx) -> None:
    client, db, lotus, jelly = ctx["client"], ctx["db"], ctx["lotus"], ctx["jelly"]

    # 1. 회원가입 → 로그인 (B)
    res = await client.post("/auth/signup", json=CUSTOMER)
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "customer"
    kim = await _login(client, CUSTOMER["email"], CUSTOMER["password"])
    admin = await _login(client, ADMIN["email"], ADMIN["password"])

    # 2. 상품 찾기 (A): 띄어쓰기를 무시한 검색 → 상세
    found = (await client.get("/products", params={"q": "로투스비스코프"})).json()
    assert [p["id"] for p in found["items"]] == [lotus]
    assert (await client.get(f"/products/{lotus}")).json()["stock"] == 10

    # 3. 장바구니 담기 (B): 같은 상품은 수량 합산
    await client.post("/cart/items", json={"productId": lotus, "quantity": 1}, headers=kim)
    cart = (await client.post("/cart/items", json={"productId": lotus, "quantity": 1}, headers=kim)).json()
    cart = (await client.post("/cart/items", json={"productId": jelly, "quantity": 1}, headers=kim)).json()
    assert [(i["id"], i["quantity"]) for i in cart["items"]] == [(lotus, 2), (jelly, 1)]
    assert cart["totalPrice"] == 4500 * 2 + 3900

    # 4. 주문하기 (B): 재고 차감 · 결제완료 · 장바구니 비움 · 이력 첫 줄을 한 번에
    res = await client.post("/orders", json=SHIPPING, headers=kim)
    assert res.status_code == 201, res.text
    order = res.json()
    order_id = order["orderId"]
    assert order["status"] == "접수" and order["totalPrice"] == 12900
    assert order["payment"]["status"] == "결제완료"
    assert (await _stock(db, lotus), await _stock(db, jelly)) == (8, 4)
    assert await db.scalar(select(CartItemModel)) is None
    assert (await client.get("/cart", headers=kim)).json()["items"] == []
    mine = (await client.get("/orders", headers=kim)).json()
    assert [o["orderId"] for o in mine["items"]] == [order_id]

    # 5. 고객은 관리자 API 를 못 써요 (C 권한)
    res = await client.patch(f"/admin/orders/{order_id}/status", json={"status": "상품준비중"}, headers=kim)
    assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN"

    # 6. 관리자 배송 처리 (C): 주문자 이름으로 찾기 → 상품준비중 → 배송중(택배사 · 운송장)
    listed = (await client.get("/admin/orders", params={"q": "김구르"}, headers=admin)).json()
    assert [o["orderId"] for o in listed["items"]] == [order_id]
    assert listed["items"][0]["nextStatuses"] == ["상품준비중", "주문취소"]

    res = await client.patch(f"/admin/orders/{order_id}/status", json={"status": "상품준비중"}, headers=admin)
    assert res.status_code == 200, res.text
    res = await client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "배송중", "courier": "CJ대한통운", "trackingNo": "1234-5678-9012"},
        headers=admin,
    )
    assert res.status_code == 200, res.text
    shipped = res.json()
    assert (shipped["status"], shipped["courier"], shipped["trackingNo"]) == ("배송중", "CJ대한통운", "1234-5678-9012")
    assert [h["status"] for h in shipped["history"]] == ["접수", "상품준비중", "배송중"]

    # 7. 고객 화면에도 배송중으로 보여요 (B)
    assert (await client.get(f"/orders/{order_id}", headers=kim)).json()["status"] == "배송중"

    # 8. 고객 취소 시도 → 409 차단, DB 는 그대로 (재고 복구 없음, 결제완료 그대로, 이력 추가 없음)
    res = await client.post(f"/orders/{order_id}/cancel", headers=kim)
    assert res.status_code == 409, res.text
    assert res.json() == {"code": "BUSINESS_RULE_VIOLATION", "message": SHIPPED_CANCEL}

    db.expire_all()
    assert await db.scalar(select(OrderModel.status).where(OrderModel.order_id == order_id)) == "배송중"
    assert await db.scalar(select(PaymentModel.status).where(PaymentModel.order_id == order_id)) == "결제완료"
    assert (await _stock(db, lotus), await _stock(db, jelly)) == (8, 4)
    admin_id = ctx["admin_id"]
    assert await _history(db, order_id) == [(None, "접수", None), ("접수", "상품준비중", admin_id), ("상품준비중", "배송중", admin_id)]

    # 9. 배송완료 뒤에도 취소 불가, 관리자도 끝난 주문은 못 바꿔요
    await client.patch(f"/admin/orders/{order_id}/status", json={"status": "배송완료"}, headers=admin)
    res = await client.post(f"/orders/{order_id}/cancel", headers=kim)
    assert res.status_code == 409 and "'배송완료' 상태의 주문은 취소할 수 없어요" in res.json()["message"]
    res = await client.patch(f"/admin/orders/{order_id}/status", json={"status": "주문취소", "note": "변심"}, headers=admin)
    assert res.status_code == 409 and res.json()["code"] == "BUSINESS_RULE_VIOLATION"
    assert (await _stock(db, lotus), await _stock(db, jelly)) == (8, 4)


async def test_customer_cancel_is_allowed_before_shipping(ctx) -> None:
    """비교용: 출고 전(접수)이면 같은 고객 취소가 통과하고 재고 · 결제가 되돌아가요."""
    client, db, lotus = ctx["client"], ctx["db"], ctx["lotus"]
    await client.post("/auth/signup", json=CUSTOMER)
    kim = await _login(client, CUSTOMER["email"], CUSTOMER["password"])

    await client.post("/cart/items", json={"productId": lotus, "quantity": 3}, headers=kim)
    order_id = (await client.post("/orders", json=SHIPPING, headers=kim)).json()["orderId"]
    assert await _stock(db, lotus) == 7

    res = await client.post(f"/orders/{order_id}/cancel", headers=kim)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "주문취소" and res.json()["payment"]["status"] == "결제취소"
    assert await _stock(db, lotus) == 10
    assert await _history(db, order_id) == [(None, "접수", None), ("접수", "주문취소", None)]


async def test_existing_search_filter_and_404_still_work(ctx) -> None:
    """회귀: 인수 때부터 있던 검색 · 필터 · 없는 상품 화면이 쓰는 API."""
    client, lotus, jelly = ctx["client"], ctx["lotus"], ctx["jelly"]

    assert (await client.get("/products", params={"q": "곤약"})).json()["total"] == 1
    assert (await client.get("/products", params={"q": "없는과자이름"})).json()["total"] == 0

    by_price = (await client.get("/products", params={"sort": "low"})).json()["items"]
    assert [p["id"] for p in by_price] == [jelly, lotus]  # 3900 → 4500

    category = (await client.get(f"/products/{lotus}")).json()["categorySlug"]
    filtered = (await client.get("/products", params={"category": category})).json()
    assert [p["id"] for p in filtered["items"]] == [lotus]

    res = await client.get("/products", params={"country": "korea"})
    assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR"

    res = await client.get("/products/999999")
    assert res.status_code == 404
    assert res.json() == {"code": "NOT_FOUND", "message": "상품을 찾을 수 없어요."}
