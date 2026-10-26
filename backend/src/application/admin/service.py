"""관리자 주문 운영 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from domain.admin.views import AdminOrderQuery, AdminOrderView, OrderSummary, Page
from domain.exceptions import NotFoundError
from domain.order.status import OrderStatus, change_by_admin, parse_status
from infrastructure.admin.repositories import (
    AdminOrderCommandRepository,
    AdminOrderQueryRepository,
    OrderStatusHistoryRepository,
)
from infrastructure.product.repositories import ProductRepository

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


def now_kst() -> datetime:
    # DB 시간 컬럼은 시간대 없이 KST 로 저장해요
    return datetime.now(KST).replace(tzinfo=None)


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


class AdminOrderStatusService:
    """관리자 상태 변경 · 취소 (PATCH /admin/orders/{orderId}/status). 한 요청 = 한 트랜잭션."""

    def __init__(self, session: AsyncSession, *, now=now_kst):
        self.session = session
        self.commands = AdminOrderCommandRepository(session)
        self.history = OrderStatusHistoryRepository(session)
        self.queries = AdminOrderQueryRepository(session)
        self.products = ProductRepository(session)
        self._now = now

    async def change_status(
        self,
        order_id: int,
        status: str | OrderStatus,
        *,
        admin_id: int | None,
        courier: str | None = None,
        tracking_no: str | None = None,
        note: str | None = None,
    ) -> AdminOrderView:
        try:
            # 1. 주문 행을 잠그고 읽어요 (SELECT … FOR UPDATE)
            order = await self.commands.lock(order_id)
            if order is None:
                raise NotFoundError("주문을 찾을 수 없어요.")

            # 2. 도메인 규칙 검사 (허용 전이 · 운송장 · 사유)
            target = status if isinstance(status, OrderStatus) else parse_status(status)
            now = self._now()
            change = change_by_admin(
                OrderStatus(order.status), target,
                changed_at=now, changed_by=admin_id, courier=courier, tracking_no=tracking_no, note=note,
            )

            # 3. 주문 갱신
            order.status = change.to_status.value
            order.updated_at = now
            if change.courier:
                order.courier, order.tracking_no = change.courier, change.tracking_no
            if change.note:
                order.admin_note = change.note

            # 4. 이력 한 줄
            await self.history.add(order_id, change)

            # 5. 취소면 재고 복구
            if change.restores_stock:
                await self._restore_stock(order_id)
                # 결제가 있으면 결제취소로 (없는 주문은 건너뛰어요)
                await self.commands.cancel_payment(order_id)

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        view = await self.queries.get(order_id)
        assert view is not None
        return view

    async def _restore_stock(self, order_id: int) -> None:
        # 상품 행을 product_id 순서로 잠그고(SELECT … FOR UPDATE) 도메인 규칙으로 재고를 늘려요 (SCRUM-21 ProductRepository)
        for product_id, quantity in await self.commands.quantities_by_product(order_id):
            product = await self.products.get_for_update(product_id)
            if product is None:
                raise NotFoundError(f"상품을 찾을 수 없어요. (상품 번호 {product_id})")
            product.increase_stock(quantity)
            await self.products.save_stock(product)
