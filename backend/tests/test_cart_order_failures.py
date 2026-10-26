"""SCRUM-40: 장바구니 · 주문 API 실패 케이스 (401 · 403 · 404 · 405 · 409 · 422, 테스트 DB).

모든 실패가 같은 모양 { code, message } 이고, 실패한 요청은 DB 를 바꾸지 않는지 다시 조회해서 확인해요.
- 400 은 나지 않아요: 형식 오류는 공통 규칙대로 모두 422 VALIDATION_ERROR 예요 (깨진 JSON 테스트).
- 성공 흐름 · 기본 실패는 test_cart_api.py · test_order_api.py · test_my_orders_api.py 에도 있어요.
토큰은 진짜 회원가입 · 로그인을 거쳐서 받아요 (get_current_user 를 바꾸지 않아요).
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from core.config import get_settings
from database import get_session
from infrastructure.cart.models import CartItemModel
from infrastructure.order.models import OrderModel, PaymentModel
from infrastructure.product.models import ProductModel
from main import app
from tests.factories import make_product

pytestmark = pytest.mark.anyio

PASSWORD = "secret-123"
SHIPPING = {"recipient": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구 테헤란로 123"}
BROKEN = "로그인 정보가 올바르지 않아요. 다시 로그인해 주세요."


@pytest.fixture
async def client(db_session):
    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def ctx(client, db_session) -> dict:
    """김구르: 주문 1건(접수, 쿠키 5개) + 장바구니에 쿠키 2개. 이망고: 빈 장바구니. 상품: 쿠키(재고 10 → 주문 뒤 5) · 품절과자(재고 0)."""
    cookie = (await make_product(db_session, name="로투스", price=4500, stock=10)).product_id
    sold_out = (await make_product(db_session, name="품절과자", price=1000, stock=0)).product_id
    await db_session.commit()
    kim, lee = await _auth(client, "kim@test.com", "김구르"), await _auth(client, "lee@test.com", "이망고")

    await client.post("/cart/items", json={"productId": cookie, "quantity": 5}, headers=kim)
    order_id = (await client.post("/orders", json=SHIPPING, headers=kim)).json()["orderId"]  # 재고 10 → 5
    await client.post("/cart/items", json={"productId": cookie, "quantity": 2}, headers=kim)
    return {"cookie": cookie, "sold_out": sold_out, "order": order_id, "kim": kim, "lee": lee}


async def _auth(client, email: str, name: str) -> dict:
    await client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": name})
    token = (await client.post("/auth/login", data={"username": email, "password": PASSWORD})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _token(member_id: int, *, key: str | None = None, **claims) -> str:
    settings = get_settings()
    payload = {"sub": str(member_id), "role": "customer", "jti": "scrum-40", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return jwt.encode({**payload, **claims}, key or settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _assert_error(res, status: int, code: str, message: str | None = None) -> None:
    body = res.json()
    assert res.status_code == status and body["code"] == code, res.text
    assert isinstance(body["message"], str) and body["message"]  # 화면이 그대로 보여 줄 문장
    if message is not None:
        assert body["message"] == message


async def _snapshot(db_session) -> dict:
    """실패 전후로 비교할 DB 상태: 장바구니 · 재고 · 주문 상태 · 주문 · 결제 수."""
    db_session.expire_all()
    return {
        "cart": (await db_session.execute(select(CartItemModel.member_id, CartItemModel.product_id, CartItemModel.quantity).order_by(CartItemModel.member_id))).all(),
        "stock": (await db_session.execute(select(ProductModel.product_id, ProductModel.stock).order_by(ProductModel.product_id))).all(),
        "orders": (await db_session.execute(select(OrderModel.order_id, OrderModel.status).order_by(OrderModel.order_id))).all(),
        "payments": (await db_session.execute(select(PaymentModel.order_id, PaymentModel.status).order_by(PaymentModel.order_id))).all(),
        "order_count": await db_session.scalar(select(func.count()).select_from(OrderModel)),
    }


def _writes(ctx) -> list[tuple[str, str, dict | None]]:
    """로그인이 필요한 장바구니 · 주문 요청 전부 (조회 포함)."""
    c, o = ctx["cookie"], ctx["order"]
    return [
        ("GET", "/cart", None),
        ("POST", "/cart/items", {"productId": c, "quantity": 1}),
        ("PATCH", f"/cart/items/{c}", {"quantity": 1}),
        ("DELETE", f"/cart/items/{c}", None),
        ("DELETE", "/cart", None),
        ("POST", "/orders", SHIPPING),
        ("GET", "/orders", None),
        ("GET", f"/orders/{o}", None),
        ("POST", f"/orders/{o}/cancel", None),
    ]


# ── 401 ──


@pytest.mark.parametrize(
    ("token", "message"),
    [
        (None, "로그인이 필요해요."),
        ("not-a-jwt", BROKEN),
        ("expired", "로그인이 만료됐어요. 다시 로그인해 주세요."),
        ("forged", BROKEN),  # 우리 서버 비밀키가 아닌 키로 서명
        ("unknown-member", BROKEN),  # 서명은 맞지만 없는 회원
    ],
)
async def test_401_on_every_cart_order_request_and_db_untouched(client, db_session, ctx, token, message) -> None:
    kim_id = (await client.get("/auth/me", headers=ctx["kim"])).json()["id"]
    value = {
        None: None,
        "not-a-jwt": "not-a-jwt",
        "expired": _token(kim_id, exp=datetime.now(UTC) - timedelta(minutes=1)),
        "forged": _token(kim_id, key="another-secret-key-for-forged-token-32b"),
        "unknown-member": _token(999999),
    }[token]
    headers = {"Authorization": f"Bearer {value}"} if value else {}
    before = await _snapshot(db_session)

    for method, path, body in _writes(ctx):
        res = await client.request(method, path, json=body, headers=headers)
        _assert_error(res, 401, "UNAUTHORIZED", message)
        assert res.headers["WWW-Authenticate"] == "Bearer"
    assert await _snapshot(db_session) == before


# ── 403: 남의 주문 ──


async def test_403_others_order_and_db_untouched(client, db_session, ctx) -> None:
    before = await _snapshot(db_session)

    get = await client.get(f"/orders/{ctx['order']}", headers=ctx["lee"])
    cancel = await client.post(f"/orders/{ctx['order']}/cancel", headers=ctx["lee"])

    _assert_error(get, 403, "FORBIDDEN", "본인 주문만 볼 수 있어요.")
    _assert_error(cancel, 403, "FORBIDDEN", "본인 주문만 볼 수 있어요.")
    assert await _snapshot(db_session) == before  # 주문 접수 · 결제완료 · 재고 그대로


async def test_others_cart_is_never_reachable(client, db_session, ctx) -> None:
    """장바구니는 경로에 회원 번호가 없어서 403 대신 '내 장바구니에 없음' 404 예요."""
    before = await _snapshot(db_session)

    res = await client.delete(f"/cart/items/{ctx['cookie']}", headers=ctx["lee"])  # 김구르 장바구니의 상품

    _assert_error(res, 404, "NOT_FOUND", "장바구니에 없는 상품이에요.")
    assert (await client.get("/cart", headers=ctx["lee"])).json()["items"] == []
    assert await _snapshot(db_session) == before


# ── 404 · 405 ──


async def test_404_missing_product_cart_item_order_or_path(client, ctx) -> None:
    kim = ctx["kim"]
    _assert_error(await client.post("/cart/items", json={"productId": 999999}, headers=kim), 404, "NOT_FOUND", "상품을 찾을 수 없어요.")
    _assert_error(await client.patch(f"/cart/items/{ctx['sold_out']}", json={"quantity": 1}, headers=kim), 404, "NOT_FOUND", "장바구니에 없는 상품이에요.")
    _assert_error(await client.get("/orders/999999", headers=kim), 404, "NOT_FOUND", "주문을 찾을 수 없어요.")
    _assert_error(await client.post("/orders/999999/cancel", headers=kim), 404, "NOT_FOUND", "주문을 찾을 수 없어요.")
    _assert_error(await client.get("/carts", headers=kim), 404, "NOT_FOUND")


@pytest.mark.parametrize(("method", "path"), [("PUT", "/cart"), ("PUT", "/orders/1"), ("DELETE", "/orders/1")])
async def test_405_unsupported_method(client, ctx, method, path) -> None:
    res = await client.request(method, path, headers=ctx["kim"])
    _assert_error(res, 405, "METHOD_NOT_ALLOWED", "이 주소에서는 지원하지 않는 요청 방식이에요.")


# ── 409: 업무 규칙 ──


async def test_409_cart_rules_and_db_untouched(client, db_session, ctx) -> None:
    kim = ctx["kim"]
    before = await _snapshot(db_session)

    sold_out = await client.post("/cart/items", json={"productId": ctx["sold_out"]}, headers=kim)
    over_merge = await client.post("/cart/items", json={"productId": ctx["cookie"], "quantity": 4}, headers=kim)  # 2 + 4 > 재고 5
    over_set = await client.patch(f"/cart/items/{ctx['cookie']}", json={"quantity": 6}, headers=kim)

    _assert_error(sold_out, 409, "BUSINESS_RULE_VIOLATION", "'품절과자' 상품이 품절이에요.")
    _assert_error(over_merge, 409, "BUSINESS_RULE_VIOLATION", "'로투스' 재고가 부족해요. (최대 5개까지 담을 수 있어요)")
    _assert_error(over_set, 409, "BUSINESS_RULE_VIOLATION", "'로투스' 재고가 부족해요. (최대 5개까지 담을 수 있어요)")
    assert await _snapshot(db_session) == before  # 장바구니 2개 그대로


async def test_409_order_rules_and_db_untouched(client, db_session, ctx) -> None:
    # 빈 장바구니로 주문
    _assert_error(await client.post("/orders", json=SHIPPING, headers=ctx["lee"]), 409, "BUSINESS_RULE_VIOLATION", "장바구니가 비어 있어요.")

    # 담아 둔 사이 재고가 1개로 → 주문 전체 롤백
    (await db_session.get(ProductModel, ctx["cookie"])).stock = 1
    await db_session.commit()
    before = await _snapshot(db_session)
    res = await client.post("/orders", json=SHIPPING, headers=ctx["kim"])
    _assert_error(res, 409, "BUSINESS_RULE_VIOLATION", "'로투스' 재고가 부족해요. (남은 수량 1개)")
    assert await _snapshot(db_session) == before  # 주문 1건 · 재고 1 · 장바구니 2개 그대로

    # 발송 뒤 고객 취소
    (await db_session.get(OrderModel, ctx["order"])).status = "배송중"
    await db_session.commit()
    before = await _snapshot(db_session)
    res = await client.post(f"/orders/{ctx['order']}/cancel", headers=ctx["kim"])
    _assert_error(res, 409, "BUSINESS_RULE_VIOLATION", "'배송중' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요.")
    assert await _snapshot(db_session) == before  # 재고 복구 없음 · 결제완료 그대로


# ── 422: 형식 · 값 오류 (400 이 아니에요) ──


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/cart/items", {"productId": 1, "quantity": 0}),
        ("POST", "/cart/items", {"productId": 1, "quantity": 1000}),
        ("POST", "/cart/items", {"productId": "쿠키"}),
        ("POST", "/cart/items", {"quantity": 1}),  # productId 없음
        ("PATCH", "/cart/items/abc", {"quantity": 1}),
        ("PATCH", "/cart/items/1", {}),
        ("GET", "/orders?status=없는상태", None),
        ("GET", "/orders?from=2026-10-31&to=2026-10-01", None),
        ("GET", "/orders?size=51", None),
        ("POST", "/orders/0/cancel", None),
    ],
)
async def test_422_bad_body_query_or_path(client, db_session, ctx, method, path, body) -> None:
    before = await _snapshot(db_session)
    res = await client.request(method, path, json=body, headers=ctx["kim"])
    assert res.status_code == 422, res.text
    assert res.json()["code"] in ("VALIDATION_ERROR", "INVALID_VALUE")
    assert await _snapshot(db_session) == before


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"recipient": "  "}, "받는 분 이름을 입력해 주세요."),
        ({"phone": "02-123-4567"}, "휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)"),
        ({"zipcode": "1234"}, "우편번호 5자리를 입력해 주세요."),
        ({"address1": ""}, "주소를 입력해 주세요."),
    ],
)
async def test_422_invalid_shipping_and_nothing_ordered(client, db_session, ctx, override, message) -> None:
    before = await _snapshot(db_session)
    res = await client.post("/orders", json={**SHIPPING, **override}, headers=ctx["kim"])
    _assert_error(res, 422, "INVALID_VALUE", message)
    assert await _snapshot(db_session) == before  # 재고 · 장바구니 그대로, 주문 없음


async def test_422_not_400_for_broken_json(client, db_session, ctx) -> None:
    before = await _snapshot(db_session)
    res = await client.post(
        "/cart/items",
        content='{"productId": 1,'.encode(),  # 닫는 괄호가 없는 JSON
        headers={**ctx["kim"], "Content-Type": "application/json"},
    )
    _assert_error(res, 422, "VALIDATION_ERROR")
    assert await _snapshot(db_session) == before
