"""관리자 주문 운영 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.order.status import OrderStatus, StatusChange
from infrastructure.admin.models import OrderStatusHistoryModel


class OrderStatusHistoryRepository:
    """주문 상태 이력 저장 · 조회. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, order_id: int, change: StatusChange) -> None:
        self.session.add(
            OrderStatusHistoryModel(
                order_id=order_id,
                from_status=change.from_status.value if change.from_status else None,
                to_status=change.to_status.value,
                changed_by=change.changed_by,
                note=change.note,
                changed_at=change.changed_at,
            )
        )
        await self.session.flush()

    async def list_by_order(self, order_id: int) -> list[StatusChange]:
        """오래된 순으로 돌려줘요 (화면 이력 표시 순서)."""
        rows = await self.session.scalars(
            select(OrderStatusHistoryModel)
            .where(OrderStatusHistoryModel.order_id == order_id)
            .order_by(OrderStatusHistoryModel.changed_at, OrderStatusHistoryModel.history_id)
        )
        return [_to_domain(row) for row in rows]


def _to_domain(row: OrderStatusHistoryModel) -> StatusChange:
    return StatusChange(
        from_status=OrderStatus(row.from_status) if row.from_status else None,
        to_status=OrderStatus(row.to_status),
        changed_at=row.changed_at,
        note=row.note,
        changed_by=row.changed_by,
    )
