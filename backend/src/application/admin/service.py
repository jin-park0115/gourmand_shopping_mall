"""관리자 주문 운영 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from domain.admin.views import AdminOrderQuery, AdminOrderView, OrderSummary, Page
from domain.exceptions import NotFoundError
from infrastructure.admin.repositories import AdminOrderQueryRepository

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


class AdminOrderQueryService:
    """관리자 화면 조회 (목록 · 요약 · 상세). 읽기만 해서 commit 하지 않아요."""

    def __init__(self, session: AsyncSession, *, today=today_kst):
        self.orders = AdminOrderQueryRepository(session)
        self._today = today

    async def list_orders(self, query: AdminOrderQuery) -> Page[AdminOrderView]:
        return await self.orders.search(query)

    async def summary(self, query: AdminOrderQuery) -> OrderSummary:
        return await self.orders.summary(query, today=self._today())

    async def get_order(self, order_id: int) -> AdminOrderView:
        order = await self.orders.get(order_id)
        if order is None:
            raise NotFoundError("주문을 찾을 수 없어요.")
        return order
