"""SCRUM-33: 주문 상태 이력 저장 · 조회 (테스트 DB, 테스트마다 rollback)."""
from datetime import datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from domain.order.status import OrderStatus, change_by_admin, received
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.admin.repositories import OrderStatusHistoryRepository
from infrastructure.auth.models import MemberModel
from infrastructure.order.models import OrderModel
from tests.factories import make_member, make_order, make_product

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 10, 23, 14, 0)
T1 = datetime(2026, 10, 23, 15, 0)
T2 = datetime(2026, 10, 24, 9, 30)


async def _order(db_session):
    admin = await make_member(db_session)
    product = await make_product(db_session)
    order = await make_order(db_session, admin, [(product, 2)])
    return admin, order


async def test_history_is_saved_and_listed_oldest_first(db_session) -> None:
    admin, order = await _order(db_session)
    repo = OrderStatusHistoryRepository(db_session)

    # 일부러 순서를 섞어서 저장해도 시간 순으로 나와야 해요
    await repo.add(order.order_id, change_by_admin(OrderStatus.RECEIVED, OrderStatus.PREPARING, changed_at=T1, changed_by=admin.member_id))
    await repo.add(order.order_id, received(changed_at=T0))
    await repo.add(
        order.order_id,
        change_by_admin(
            OrderStatus.PREPARING, OrderStatus.SHIPPING, changed_at=T2, changed_by=admin.member_id,
            courier="CJ대한통운", tracking_no="1234567890",
        ),
    )

    history = await repo.list_by_order(order.order_id)
    assert [(h.from_status, h.to_status) for h in history] == [
        (None, OrderStatus.RECEIVED),
        (OrderStatus.RECEIVED, OrderStatus.PREPARING),
        (OrderStatus.PREPARING, OrderStatus.SHIPPING),
    ]
    assert [h.changed_at for h in history] == [T0, T1, T2]
    assert history[0].changed_by is None
    assert history[1].changed_by == admin.member_id


async def test_note_is_kept(db_session) -> None:
    admin, order = await _order(db_session)
    repo = OrderStatusHistoryRepository(db_session)
    await repo.add(order.order_id, change_by_admin(OrderStatus.RECEIVED, OrderStatus.CANCELLED, changed_at=T1, note="품절"))
    [entry] = await repo.list_by_order(order.order_id)
    assert entry.note == "품절"
    assert entry.restores_stock


async def test_history_of_other_order_is_not_mixed(db_session) -> None:
    admin, order = await _order(db_session)
    other = await make_order(db_session, admin, [(await make_product(db_session, name="포키"), 1)])
    repo = OrderStatusHistoryRepository(db_session)
    await repo.add(order.order_id, received(changed_at=T0))
    await repo.add(other.order_id, received(changed_at=T1))
    assert len(await repo.list_by_order(order.order_id)) == 1
    assert await repo.list_by_order(9999) == []


async def test_invalid_status_is_rejected_by_db(db_session) -> None:
    _, order = await _order(db_session)
    db_session.add(OrderStatusHistoryModel(order_id=order.order_id, to_status="반품", changed_at=T0))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_history_is_deleted_with_order(db_session) -> None:
    _, order = await _order(db_session)
    await OrderStatusHistoryRepository(db_session).add(order.order_id, received(changed_at=T0))
    await db_session.execute(delete(OrderModel).where(OrderModel.order_id == order.order_id))
    left = await db_session.scalars(select(OrderStatusHistoryModel).where(OrderStatusHistoryModel.order_id == order.order_id))
    assert left.all() == []


async def test_history_survives_when_admin_is_deleted(db_session) -> None:
    admin, order = await _order(db_session)
    repo = OrderStatusHistoryRepository(db_session)
    await repo.add(order.order_id, change_by_admin(OrderStatus.RECEIVED, OrderStatus.PREPARING, changed_at=T1, changed_by=admin.member_id))
    # 주문의 회원과 이력의 관리자를 다르게 두고, 관리자만 지워요
    other_admin = await make_member(db_session, email="admin2@test.com")
    await repo.add(order.order_id, change_by_admin(OrderStatus.PREPARING, OrderStatus.CANCELLED, changed_at=T2, changed_by=other_admin.member_id, note="품절"))
    admin_id, order_id = admin.member_id, order.order_id
    await db_session.execute(delete(MemberModel).where(MemberModel.member_id == other_admin.member_id))
    db_session.expire_all()
    history = await repo.list_by_order(order_id)
    assert [h.changed_by for h in history] == [admin_id, None]
