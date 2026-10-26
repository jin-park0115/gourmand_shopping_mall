"""SCRUM-43: 관리자 주문 API 실패 케이스 (401 · 403 · 404 · 405 · 409 · 422, 테스트 DB).

모든 실패가 같은 모양 { code, message } 이고, 화면이 message 를 그대로 보여 줄 수 있는지 확인해요.
400 은 관리자 API 에서 나지 않아요: 형식 오류는 공통 규칙대로 모두 422 VALIDATION_ERROR 예요 (아래 깨진 JSON 테스트).
SCRUM-34 · 35 의 기본 실패는 test_admin_api.py, 로그아웃한 토큰은 test_admin_logout.py 에 있어요.
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from core.config import get_settings
from database import get_session
from domain.auth.member import CurrentUser, MemberRole
from infrastructure.admin.models import OrderStatusHistoryModel
from main import app
from presentation.auth.dependencies import get_current_user
from tests.factories import make_member, make_order, make_product

pytestmark = pytest.mark.anyio


@pytest.fixture
async def ctx(db_session):
    admin = await make_member(db_session)
    customer = await make_member(db_session, email="c@test.com", role="customer")
    lotus = await make_product(db_session, name="로투스", price=4500, stock=10)
    preparing = await make_order(db_session, customer, [(lotus, 2)], status="상품준비중")
    shipping = await make_order(db_session, customer, [(lotus, 1)], status="배송중")
    delivered = await make_order(db_session, customer, [(lotus, 1)], status="배송완료")
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    yield {
        "admin": CurrentUser(member_id=admin.member_id, email=admin.email, role=MemberRole.ADMIN),
        "customer": CurrentUser(member_id=customer.member_id, email=customer.email, role=MemberRole.CUSTOMER),
        "admin_id": admin.member_id,
        "preparing": preparing.order_id,
        "shipping": shipping.order_id,
        "delivered": delivered.order_id,
    }
    app.dependency_overrides.clear()


def _login(user: CurrentUser) -> None:
    async def _user():
        return user

    app.dependency_overrides[get_current_user] = _user


@pytest.fixture
async def anon():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin(ctx, anon):
    _login(ctx["admin"])
    return anon


def _assert_error(res, status: int, code: str, message: str | None = None) -> None:
    body = res.json()
    assert res.status_code == status and body["code"] == code, res.text
    assert isinstance(body["message"], str) and body["message"]  # 화면이 그대로 보여 줄 문장
    if message is not None:
        assert body["message"] == message
    assert res.headers["X-Request-ID"]  # 서버 로그와 이어 볼 수 있어요 (SCRUM-17)


def _token(admin_id: int, **claims) -> str:
    settings = get_settings()
    payload = {"sub": str(admin_id), "role": "admin", "jti": "scrum-43", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return jwt.encode({**payload, **claims}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


ENDPOINTS = [
    ("GET", "/admin/orders", None),
    ("GET", "/admin/orders/summary", None),
    ("GET", "/admin/orders/{preparing}", None),
    ("PATCH", "/admin/orders/{preparing}/status", {"status": "주문취소", "note": "테스트"}),
]


# ── 401: 로그인이 안 됐거나 토큰을 믿을 수 없어요 (진짜 get_current_user 를 거쳐요) ──


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
async def test_401_without_token_on_every_endpoint(ctx, anon, method, path, body) -> None:
    res = await anon.request(method, path.format(**ctx), json=body)
    _assert_error(res, 401, "UNAUTHORIZED", "로그인이 필요해요.")
    assert res.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("token", "message"),
    [
        ("not-a-jwt", "로그인 정보가 올바르지 않아요. 다시 로그인해 주세요."),
        ("expired", "로그인이 만료됐어요. 다시 로그인해 주세요."),
        ("forged", "로그인 정보가 올바르지 않아요. 다시 로그인해 주세요."),
    ],
)
async def test_401_for_broken_expired_or_forged_token(ctx, anon, token, message) -> None:
    value = {
        "not-a-jwt": "not-a-jwt",
        "expired": _token(ctx["admin_id"], exp=datetime.now(UTC) - timedelta(minutes=1)),
        "forged": jwt.encode(  # 우리 서버 비밀키가 아닌 키로 서명한 토큰
            {"sub": str(ctx["admin_id"]), "role": "admin", "jti": "x", "exp": datetime.now(UTC) + timedelta(minutes=5)},
            "another-secret-key-for-forged-token",
            algorithm="HS256",
        ),
    }[token]
    res = await anon.get("/admin/orders", headers={"Authorization": f"Bearer {value}"})
    _assert_error(res, 401, "UNAUTHORIZED", message)


# ── 403: 로그인은 했지만 고객 계정이에요 ──


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
async def test_403_for_customer_on_every_endpoint(ctx, anon, db_session, method, path, body) -> None:
    _login(ctx["customer"])
    res = await anon.request(method, path.format(**ctx), json=body)
    _assert_error(res, 403, "FORBIDDEN", "관리자만 사용할 수 있어요.")
    # 고객이 취소를 시도해도 이력이 생기지 않아요
    history = await db_session.scalars(select(OrderStatusHistoryModel).where(OrderStatusHistoryModel.order_id == ctx["preparing"]))
    assert history.all() == []


# ── 404 · 405: 없는 주문 · 없는 경로 · 지원하지 않는 메서드 ──


async def test_404_for_missing_order_and_path(admin) -> None:
    _assert_error(await admin.get("/admin/orders/999999"), 404, "NOT_FOUND", "주문을 찾을 수 없어요.")
    res = await admin.patch("/admin/orders/999999/status", json={"status": "상품준비중"})
    _assert_error(res, 404, "NOT_FOUND", "주문을 찾을 수 없어요.")
    _assert_error(await admin.get("/admin/order"), 404, "NOT_FOUND")


async def test_405_for_unsupported_method(ctx, admin) -> None:
    _assert_error(await admin.delete(f"/admin/orders/{ctx['preparing']}"), 405, "METHOD_NOT_ALLOWED")


# ── 409: 지금 상태에서 할 수 없는 변경 ──


async def test_409_when_the_same_change_is_sent_twice(ctx, admin) -> None:
    # 두 관리자가 같은 주문을 동시에 출고하거나, 버튼을 두 번 누른 경우: 두 번째는 바뀐 상태로 검사돼요
    body = {"status": "배송중", "courier": "CJ대한통운", "trackingNo": "1234-5678-9012"}
    assert (await admin.patch(f"/admin/orders/{ctx['preparing']}/status", json=body)).status_code == 200
    res = await admin.patch(f"/admin/orders/{ctx['preparing']}/status", json=body)
    _assert_error(res, 409, "BUSINESS_RULE_VIOLATION", "이미 '배송중' 상태예요.")


async def test_409_for_finished_order(ctx, admin) -> None:
    res = await admin.patch(f"/admin/orders/{ctx['delivered']}/status", json={"status": "주문취소", "note": "늦은 취소"})
    _assert_error(res, 409, "BUSINESS_RULE_VIOLATION", "'배송완료' 상태에서 '주문취소'(으)로 바꿀 수 없어요.")


# ── 422: 형식 오류(VALIDATION_ERROR) · 업무 규칙상 틀린 값(INVALID_VALUE) ──


@pytest.mark.parametrize(
    "path",
    ["/admin/orders?page=0", "/admin/orders?size=101", "/admin/orders?q=" + "가" * 51, "/admin/orders/0", "/admin/orders/abc"],
)
async def test_422_for_bad_query_or_path(admin, path) -> None:
    _assert_error(await admin.get(path), 422, "VALIDATION_ERROR")


async def test_422_not_400_for_broken_json(ctx, admin) -> None:
    res = await admin.patch(
        f"/admin/orders/{ctx['preparing']}/status",
        content='{"status": "배송중",'.encode(),  # 닫는 괄호가 없는 JSON
        headers={"Content-Type": "application/json"},
    )
    _assert_error(res, 422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("order", "body", "message"),
    [
        ("preparing", {"status": "배송중", "courier": "대한택배", "trackingNo": "1234-5678-9012"}, None),
        ("preparing", {"status": "배송중", "courier": "CJ대한통운", "trackingNo": "abc"}, "운송장 번호는 숫자와 '-'로 8~20자여야 해요."),
        ("preparing", {"status": "주문취소"}, None),
        ("shipping", {"status": "배송지연"}, "'배송지연'(으)로 바꾸려면 사유를 입력해 주세요."),
    ],
)
async def test_422_invalid_value_leaves_order_untouched(ctx, admin, db_session, order, body, message) -> None:
    res = await admin.patch(f"/admin/orders/{ctx[order]}/status", json=body)
    _assert_error(res, 422, "INVALID_VALUE", message)
    detail = (await admin.get(f"/admin/orders/{ctx[order]}")).json()
    assert detail["status"] == ("상품준비중" if order == "preparing" else "배송중")
    history = await db_session.scalars(select(OrderStatusHistoryModel).where(OrderStatusHistoryModel.order_id == ctx[order]))
    assert history.all() == []
