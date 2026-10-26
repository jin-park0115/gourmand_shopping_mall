"""SCRUM-34: 관리자 주문 목록 · 요약 · 상세 조회 (테스트 DB, 테스트마다 rollback)."""
from datetime import date, datetime

import pytest

from application.admin.service import AdminOrderQueryService
from domain.admin.views import AdminOrderQuery
from domain.exceptions import InvalidValueError, NotFoundError
from domain.order.status import OrderStatus, change_by_admin, received
from infrastructure.admin.repositories import OrderStatusHistoryRepository
from tests.factories import make_member, make_order, make_product

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 23)
S = OrderStatus


@pytest.fixture
async def shop(db_session):
    """주문 5건: 상태 · 날짜 · 받는 사람 · 상품을 섞어 둬요."""
    customer = await make_member(db_session, email="c@test.com", role="customer")
    lotus = await make_product(db_session, name="로투스 비스코프", price=4500)
    pocky = await make_product(db_session, name="포키 초코", price=2000)
    jelly = await make_product(db_session, name="하리보 골드베렌", price=3000)
    o1 = await make_order(db_session, customer, [(lotus, 2)], status="접수", recipient="김구르", phone="010-1111-2222",
                          ordered_at=datetime(2026, 10, 23, 9, 0))
    o2 = await make_order(db_session, customer, [(pocky, 3), (lotus, 1)], status="배송중", recipient="이망고",
                          phone="010-3333-4444", ordered_at=datetime(2026, 10, 23, 11, 0))
    o3 = await make_order(db_session, customer, [(jelly, 5)], status="주문취소", recipient="박젤리",
                          phone="010-5555-6666", ordered_at=datetime(2026, 10, 23, 12, 0))
    o4 = await make_order(db_session, customer, [(pocky, 1)], status="상품준비중", recipient="김구르",
                          phone="010-1111-2222", ordered_at=datetime(2026, 10, 21, 18, 0))
    o5 = await make_order(db_session, customer, [(lotus, 4)], status="배송완료", recipient="최쿠키",
                          phone="010-7777-8888", ordered_at=datetime(2026, 10, 20, 23, 59))
    return {"orders": [o1, o2, o3, o4, o5], "lotus": lotus, "pocky": pocky, "jelly": jelly}


def _service(db_session) -> AdminOrderQueryService:
    return AdminOrderQueryService(db_session, today=lambda: TODAY)


def _ids(page) -> list[int]:
    return [o.order_id for o in page.items]


async def test_list_is_newest_first_with_lines(db_session, shop) -> None:
    o1, o2, o3, o4, o5 = shop["orders"]
    page = await _service(db_session).list_orders(AdminOrderQuery())
    assert _ids(page) == [o3.order_id, o2.order_id, o1.order_id, o4.order_id, o5.order_id]
    assert (page.total, page.page, page.size, page.pages) == (5, 1, 20, 1)
    second = page.items[1]
    assert [(i.name, i.price, i.quantity) for i in second.items] == [("포키 초코", 2000, 3), ("로투스 비스코프", 4500, 1)]
    assert second.buyer.name == "이망고"
    assert second.history is None  # 목록에는 이력을 싣지 않아요
    assert second.next_statuses == [S.DELIVERED, S.DELAYED]


async def test_pagination(db_session, shop) -> None:
    o1, o2, o3, o4, o5 = shop["orders"]
    page2 = await _service(db_session).list_orders(AdminOrderQuery(page=2, size=2))
    assert _ids(page2) == [o1.order_id, o4.order_id]
    assert (page2.total, page2.pages) == (5, 3)
    empty = await _service(db_session).list_orders(AdminOrderQuery(page=9, size=2))
    assert empty.items == [] and empty.total == 5


async def test_filter_by_status(db_session, shop) -> None:
    page = await _service(db_session).list_orders(AdminOrderQuery(status=S.SHIPPING))
    assert [o.status for o in page.items] == [S.SHIPPING]


@pytest.mark.parametrize(
    ("q", "expected_index"),
    [
        ("김구르", [0, 3]),  # 받는 사람 이름 (부분 일치)
        ("구르", [0, 3]),
        ("3333", [1]),  # 연락처 부분 일치
        ("하리보", [2]),  # 상품명
        ("로투스", [0, 1, 4]),  # 상품명 — 여러 상품 중 하나라도 맞으면
    ],
)
async def test_search_by_q(db_session, shop, q, expected_index) -> None:
    orders = shop["orders"]
    page = await _service(db_session).list_orders(AdminOrderQuery(q=q))
    assert sorted(_ids(page)) == sorted(orders[i].order_id for i in expected_index)


async def test_search_by_exact_order_id(db_session, shop) -> None:
    o4 = shop["orders"][3]
    page = await _service(db_session).list_orders(AdminOrderQuery(q=str(o4.order_id)))
    assert o4.order_id in _ids(page)


async def test_phone_without_hyphens(db_session, shop) -> None:
    o2 = shop["orders"][1]
    page = await _service(db_session).list_orders(AdminOrderQuery(q="01033334444"))
    assert _ids(page) == [o2.order_id]


async def test_hyphen_only_query_does_not_match_everything(db_session, shop) -> None:
    page = await _service(db_session).list_orders(AdminOrderQuery(q="-"))
    assert page.total == 0


async def test_superscript_digit_query_is_safe(db_session, shop) -> None:
    page = await _service(db_session).list_orders(AdminOrderQuery(q="²"))
    assert page.total == 0


async def test_like_wildcards_are_escaped(db_session, shop) -> None:
    page = await _service(db_session).list_orders(AdminOrderQuery(q="%"))
    assert page.total == 0


async def test_filter_by_date_range_includes_end_day(db_session, shop) -> None:
    o1, o2, o3, o4, o5 = shop["orders"]
    page = await _service(db_session).list_orders(AdminOrderQuery(date_from=date(2026, 10, 20), date_to=date(2026, 10, 21)))
    assert _ids(page) == [o4.order_id, o5.order_id]
    only_today = await _service(db_session).list_orders(AdminOrderQuery(date_from=TODAY, date_to=TODAY))
    assert only_today.total == 3


async def test_summary(db_session, shop) -> None:
    summary = await _service(db_session).summary(AdminOrderQuery())
    assert summary.total == 5
    assert summary.status_counts == {S.RECEIVED: 1, S.PREPARING: 1, S.SHIPPING: 1, S.DELIVERED: 1, S.DELAYED: 0, S.CANCELLED: 1}
    assert summary.today_orders == 3  # 취소 포함
    assert summary.today_sales == 4500 * 2 + (2000 * 3 + 4500)  # 취소(하리보) 제외
    assert summary.today_units == 2 + 4
    assert summary.waiting_shipment == 2
    # 취소 제외 수량: 로투스 2+1+4=7, 포키 3+1=4, 하리보는 취소라 빠져요
    assert [(p.name, p.units) for p in summary.top_products] == [("로투스 비스코프", 7), ("포키 초코", 4)]


async def test_summary_follows_filters_but_today_does_not(db_session, shop) -> None:
    summary = await _service(db_session).summary(AdminOrderQuery(date_from=date(2026, 10, 20), date_to=date(2026, 10, 21)))
    assert summary.total == 2
    assert summary.status_counts[S.PREPARING] == 1 and summary.status_counts[S.DELIVERED] == 1
    assert summary.today_orders == 3  # 기간 조건과 상관없이 오늘 기준
    assert [(p.name, p.units) for p in summary.top_products] == [("로투스 비스코프", 4), ("포키 초코", 1)]


async def test_detail_includes_history(db_session, shop) -> None:
    o4 = shop["orders"][3]
    history = OrderStatusHistoryRepository(db_session)
    await history.add(o4.order_id, received(changed_at=datetime(2026, 10, 21, 18, 0)))
    await history.add(o4.order_id, change_by_admin(S.RECEIVED, S.PREPARING, changed_at=datetime(2026, 10, 22, 9, 0)))
    order = await _service(db_session).get_order(o4.order_id)
    assert order.status is S.PREPARING
    assert [h.to_status for h in order.history] == [S.RECEIVED, S.PREPARING]
    assert order.next_statuses == [S.SHIPPING, S.CANCELLED]


async def test_detail_not_found(db_session, shop) -> None:
    with pytest.raises(NotFoundError, match="주문을 찾을 수 없어요"):
        await _service(db_session).get_order(999999)


def test_query_rules() -> None:
    with pytest.raises(InvalidValueError, match="시작일이 종료일보다 늦어요"):
        AdminOrderQuery(date_from=date(2026, 10, 24), date_to=date(2026, 10, 23))
    with pytest.raises(InvalidValueError, match="size"):
        AdminOrderQuery(size=500)
    with pytest.raises(InvalidValueError, match="page"):
        AdminOrderQuery(page=0)
    with pytest.raises(InvalidValueError, match="50자"):
        AdminOrderQuery(q="가" * 51)
    assert AdminOrderQuery(q="   ").q is None
    assert AdminOrderQuery(q=" 김구르 ").q == "김구르"
