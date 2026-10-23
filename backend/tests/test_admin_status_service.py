"""SCRUM-35: 관리자 상태 변경 · 취소 서비스 (테스트 DB, 테스트마다 rollback)."""
from datetime import datetime

import pytest
from sqlalchemy import func, select

from application.admin.service import AdminOrderStatusService
from domain.exceptions import BusinessRuleError, InvalidValueError, NotFoundError
from domain.order.status import OrderStatus
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.order.models import OrderModel
from infrastructure.product.models import ProductModel
from tests.factories import make_member, make_order, make_product

pytestmark = pytest.mark.anyio

S = OrderStatus
NOW = datetime(2026, 10, 23, 16, 0)


@pytest.fixture
async def ctx(db_session):
    admin = await make_member(db_session)
    customer = await make_member(db_session, email="c@test.com", role="customer")
    lotus = await make_product(db_session, name="로투스", price=4500, stock=10)
    pocky = await make_product(db_session, name="포키", price=2000, stock=5)
    order = await make_order(db_session, customer, [(lotus, 2), (pocky, 3)], status="상품준비중")
    # 실제처럼 주문이 이미 저장돼 있어야, 서비스가 실패해서 rollback 해도 주문은 남아요 (바깥 테스트 트랜잭션은 끝에 rollback)
    await db_session.commit()
    return {
        "admin_id": admin.member_id,
        "order_id": order.order_id,
        "lotus_id": lotus.product_id,
        "pocky_id": pocky.product_id,
        "service": AdminOrderStatusService(db_session, now=lambda: NOW),
    }


async def _stock(db_session, product_id: int) -> int:
    return await db_session.scalar(select(ProductModel.stock).where(ProductModel.product_id == product_id))


async def _history_count(db_session, order_id: int) -> int:
    return await db_session.scalar(
        select(func.count()).select_from(OrderStatusHistoryModel).where(OrderStatusHistoryModel.order_id == order_id)
    )


async def test_ship_saves_courier_tracking_and_history(db_session, ctx) -> None:
    view = await ctx["service"].change_status(
        ctx["order_id"], "배송중", admin_id=ctx["admin_id"], courier="CJ대한통운", tracking_no="1234-5678-9012"
    )
    assert view.status is S.SHIPPING
    assert (view.courier, view.tracking_no) == ("CJ대한통운", "1234-5678-9012")
    assert view.next_statuses == [S.DELIVERED, S.DELAYED]
    [entry] = view.history
    assert (entry.from_status, entry.to_status, entry.changed_by, entry.changed_at) == (S.PREPARING, S.SHIPPING, ctx["admin_id"], NOW)
    row = await db_session.get(OrderModel, ctx["order_id"])
    assert row.updated_at == NOW


async def test_delay_then_resume_keeps_tracking(db_session, ctx) -> None:
    svc = ctx["service"]
    await svc.change_status(ctx["order_id"], "배송중", admin_id=ctx["admin_id"], courier="한진택배", tracking_no="5123456789")
    delayed = await svc.change_status(ctx["order_id"], "배송지연", admin_id=ctx["admin_id"], note="태풍으로 지연")
    assert delayed.admin_note == "태풍으로 지연"
    resumed = await svc.change_status(ctx["order_id"], "배송중", admin_id=ctx["admin_id"])
    assert (resumed.status, resumed.courier, resumed.tracking_no) == (S.SHIPPING, "한진택배", "5123456789")
    assert [h.to_status for h in resumed.history] == [S.SHIPPING, S.DELAYED, S.SHIPPING]


async def test_cancel_restores_stock(db_session, ctx) -> None:
    view = await ctx["service"].change_status(ctx["order_id"], "주문취소", admin_id=ctx["admin_id"], note="품절")
    assert view.status is S.CANCELLED and view.admin_note == "품절" and view.next_statuses == []
    assert await _stock(db_session, ctx["lotus_id"]) == 12
    assert await _stock(db_session, ctx["pocky_id"]) == 8


async def test_second_cancel_is_rejected_and_stock_restored_once(db_session, ctx) -> None:
    svc = ctx["service"]
    await svc.change_status(ctx["order_id"], "주문취소", admin_id=ctx["admin_id"], note="품절")
    with pytest.raises(BusinessRuleError, match="이미 '주문취소'"):
        await svc.change_status(ctx["order_id"], "주문취소", admin_id=ctx["admin_id"], note="다시")
    assert await _stock(db_session, ctx["lotus_id"]) == 12  # 두 번 복구되지 않아요


@pytest.mark.parametrize(
    ("status", "kwargs", "error", "match"),
    [
        ("배송완료", {}, BusinessRuleError, "바꿀 수 없어요"),  # 상품준비중 → 배송완료 불가
        ("배송중", {}, InvalidValueError, "운송장"),
        ("배송중", {"courier": "아무택배", "tracking_no": "1234567890"}, InvalidValueError, "택배사"),
        ("주문취소", {"note": "  "}, InvalidValueError, "사유"),
        ("반품", {}, InvalidValueError, "알 수 없는 주문 상태"),
    ],
)
async def test_rejected_change_leaves_nothing(db_session, ctx, status, kwargs, error, match) -> None:
    with pytest.raises(error, match=match):
        await ctx["service"].change_status(ctx["order_id"], status, admin_id=ctx["admin_id"], **kwargs)
    row = await db_session.get(OrderModel, ctx["order_id"])
    assert row.status == "상품준비중" and row.courier is None
    assert await _history_count(db_session, ctx["order_id"]) == 0
    assert await _stock(db_session, ctx["lotus_id"]) == 10


async def test_not_found(db_session, ctx) -> None:
    with pytest.raises(NotFoundError, match="주문을 찾을 수 없어요"):
        await ctx["service"].change_status(999999, "배송중", admin_id=ctx["admin_id"])
