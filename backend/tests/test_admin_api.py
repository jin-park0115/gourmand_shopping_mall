"""SCRUM-34 · 35: 관리자 주문 API (테스트 DB, 테스트마다 rollback).

로그인(SCRUM-19)은 get_current_user 를 바꿔 끼워서 흉내 내요. require_admin 의 403 규칙은 그대로 거쳐요.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from database import get_session
from domain.auth.member import CurrentUser, MemberRole
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.product.models import ProductModel
from main import app
from presentation.auth.dependencies import get_current_user
from tests.factories import make_member, make_order, make_product

pytestmark = pytest.mark.anyio


@pytest.fixture
async def ctx(db_session):
    admin = await make_member(db_session)
    customer = await make_member(db_session, email="c@test.com", role="customer")
    lotus = await make_product(db_session, name="로투스", price=4500, stock=10)
    received = await make_order(db_session, customer, [(lotus, 1)], status="접수", recipient="박접수")
    preparing = await make_order(db_session, customer, [(lotus, 2)], status="상품준비중", recipient="이준비")
    # 서비스가 실패해서 rollback 해도 주문은 남게 먼저 저장해요 (바깥 테스트 트랜잭션은 끝에 rollback)
    await db_session.commit()

    async def _session():
        yield db_session

    app.dependency_overrides[get_session] = _session
    yield {
        "admin": CurrentUser(member_id=admin.member_id, email=admin.email, role=MemberRole.ADMIN),
        "customer": CurrentUser(member_id=customer.member_id, email=customer.email, role=MemberRole.CUSTOMER),
        "received": received.order_id,
        "preparing": preparing.order_id,
        "lotus": lotus.product_id,
    }
    app.dependency_overrides.clear()


def _login(user: CurrentUser) -> None:
    async def _user():
        return user

    app.dependency_overrides[get_current_user] = _user


@pytest.fixture
async def client(ctx):
    _login(ctx["admin"])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_requires_login_and_admin(ctx) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.get("/admin/orders")
        assert res.status_code == 401 and res.json()["code"] == "UNAUTHORIZED"
        _login(ctx["customer"])
        res = await c.patch(f"/admin/orders/{ctx['preparing']}/status", json={"status": "주문취소", "note": "x"})
        assert res.status_code == 403 and res.json()["code"] == "FORBIDDEN"


async def test_list_returns_page_in_camel_case(client, ctx) -> None:
    body = (await client.get("/admin/orders", params={"size": 1})).json()
    assert (body["total"], body["page"], body["size"], body["pages"]) == (2, 1, 1, 2)
    [order] = body["items"]
    assert order["orderId"] == ctx["preparing"]  # 최신 주문부터
    assert order["buyer"]["buyerName"] == "이준비" and order["nextStatuses"] == ["배송중", "주문취소"]
    assert order["orderedAt"].endswith("+09:00") and order["history"] is None


async def test_list_filters_and_validation(client, ctx) -> None:
    body = (await client.get("/admin/orders", params={"status": "접수"})).json()
    assert [o["orderId"] for o in body["items"]] == [ctx["received"]]
    assert (await client.get("/admin/orders", params={"q": "이준비"})).json()["total"] == 1

    for params in ({"status": "취소"}, {"size": 500}, {"from": "2026-13-01"}):
        res = await client.get("/admin/orders", params=params)
        assert res.status_code == 422 and res.json()["code"] == "VALIDATION_ERROR", params
    res = await client.get("/admin/orders", params={"from": "2026-10-23", "to": "2026-10-20"})
    assert res.status_code == 422 and res.json() == {"code": "INVALID_VALUE", "message": "시작일이 종료일보다 늦어요."}


async def test_summary_is_not_taken_as_order_id(client) -> None:
    res = await client.get("/admin/orders/summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 2 and body["waitingShipment"] == 2
    assert set(body["statusCounts"]) == {"접수", "상품준비중", "배송중", "배송완료", "배송지연", "주문취소"}


async def test_summary_with_search_query(client) -> None:
    # 대시보드에서 검색하면 요약도 같은 q 로 불려요. 상품명 · 받는 사람 · 없는 값 모두 200
    for q, total in (("로투스", 2), ("박접수", 1), ("없는상품", 0)):
        res = await client.get("/admin/orders/summary", params={"q": q})
        assert res.status_code == 200, (q, res.text)
        assert res.json()["total"] == total, q


async def test_detail_and_not_found(client, ctx) -> None:
    body = (await client.get(f"/admin/orders/{ctx['received']}")).json()
    assert body["orderId"] == ctx["received"] and body["history"] == []
    res = await client.get("/admin/orders/999999")
    assert res.status_code == 404 and res.json() == {"code": "NOT_FOUND", "message": "주문을 찾을 수 없어요."}
    assert (await client.get("/admin/orders/abc")).status_code == 422


async def test_ship_records_admin_in_history(client, db_session, ctx) -> None:
    res = await client.patch(
        f"/admin/orders/{ctx['preparing']}/status",
        json={"status": "배송중", "courier": "CJ대한통운", "trackingNo": "1234-5678-9012"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["status"], body["courier"], body["trackingNo"]) == ("배송중", "CJ대한통운", "1234-5678-9012")
    assert [h["status"] for h in body["history"]] == ["배송중"]
    changed_by = await db_session.scalar(
        select(OrderStatusHistoryModel.changed_by).where(OrderStatusHistoryModel.order_id == ctx["preparing"])
    )
    assert changed_by == ctx["admin"].member_id


async def test_cancel_restores_stock(client, db_session, ctx) -> None:
    res = await client.patch(f"/admin/orders/{ctx['preparing']}/status", json={"status": "주문취소", "note": "품절"})
    assert res.status_code == 200, res.text
    assert res.json()["adminNote"] == "품절" and res.json()["nextStatuses"] == []
    stock = await db_session.scalar(select(ProductModel.stock).where(ProductModel.product_id == ctx["lotus"]))
    assert stock == 12


@pytest.mark.parametrize(
    ("order", "body", "status", "code"),
    [
        ("received", {"status": "배송완료"}, 409, "BUSINESS_RULE_VIOLATION"),
        ("preparing", {"status": "배송중"}, 422, "INVALID_VALUE"),  # 택배사 · 운송장 없음
        ("preparing", {"status": "주문취소", "note": "가" * 301}, 422, "VALIDATION_ERROR"),
        ("preparing", {"status": "취소"}, 422, "VALIDATION_ERROR"),
    ],
)
async def test_change_status_errors(client, ctx, order, body, status, code) -> None:
    res = await client.patch(f"/admin/orders/{ctx[order]}/status", json=body)
    assert res.status_code == status and res.json()["code"] == code, res.text
