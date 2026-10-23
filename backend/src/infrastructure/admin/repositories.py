"""관리자 주문 운영 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.admin.views import (
    AdminOrderQuery,
    AdminOrderView,
    BuyerView,
    OrderLineView,
    OrderSummary,
    Page,
    TopProduct,
)
from domain.order.status import OrderStatus, StatusChange
from infrastructure.admin.models import OrderStatusHistoryModel
from infrastructure.order.models import OrderItemModel, OrderModel
from infrastructure.product.models import ProductModel

TOP_PRODUCT_LIMIT = 5
_CANCELLED = OrderStatus.CANCELLED.value
_BEFORE_SHIPMENT = (OrderStatus.RECEIVED, OrderStatus.PREPARING)


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


class AdminOrderQueryRepository:
    """관리자 화면 조회 전용: 목록 · 상세 · 요약 (docs/API.md 'C 관리자 주문')."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.history = OrderStatusHistoryRepository(session)

    async def search(self, query: AdminOrderQuery) -> Page[AdminOrderView]:
        conditions = _conditions(query, with_status=True)
        total = await self.session.scalar(select(func.count()).select_from(OrderModel).where(*conditions))
        rows = await self.session.scalars(
            _with_lines(select(OrderModel))
            .where(*conditions)
            .order_by(OrderModel.ordered_at.desc(), OrderModel.order_id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        return Page(items=[_to_view(row) for row in rows], total=total or 0, page=query.page, size=query.size)

    async def get(self, order_id: int) -> AdminOrderView | None:
        row = await self.session.scalar(_with_lines(select(OrderModel)).where(OrderModel.order_id == order_id))
        if row is None:
            return None
        return _to_view(row, history=await self.history.list_by_order(order_id))

    async def summary(self, query: AdminOrderQuery, *, today: date) -> OrderSummary:
        # 상태별 개수 · TOP 5 는 검색 조건(q · 기간)을 따르고, today… 값은 조건과 상관없이 오늘 기준이에요
        conditions = _conditions(query, with_status=False)
        counted = dict(
            (await self.session.execute(
                select(OrderModel.status, func.count()).where(*conditions).group_by(OrderModel.status)
            )).all()
        )
        status_counts = {s: counted.get(s.value, 0) for s in OrderStatus}

        today_range = _day_range(today, today)
        today_orders = await self.session.scalar(select(func.count()).select_from(OrderModel).where(*today_range))
        live_today = (*today_range, OrderModel.status != _CANCELLED)
        today_sales = await self.session.scalar(select(func.coalesce(func.sum(OrderModel.total_price), 0)).where(*live_today))
        today_units = await self.session.scalar(
            select(func.coalesce(func.sum(OrderItemModel.quantity), 0))
            .join(OrderModel, OrderModel.order_id == OrderItemModel.order_id)
            .where(*live_today)
        )

        units = func.sum(OrderItemModel.quantity).label("units")
        top_rows = await self.session.execute(
            select(ProductModel.product_id, ProductModel.name, ProductModel.image_url, units)
            .join(OrderItemModel, OrderItemModel.product_id == ProductModel.product_id)
            .join(OrderModel, OrderModel.order_id == OrderItemModel.order_id)
            .where(*conditions, OrderModel.status != _CANCELLED)
            .group_by(ProductModel.product_id, ProductModel.name, ProductModel.image_url)
            .order_by(units.desc(), ProductModel.product_id)
            .limit(TOP_PRODUCT_LIMIT)
        )
        return OrderSummary(
            total=sum(status_counts.values()),
            status_counts=status_counts,
            today_orders=today_orders or 0,
            today_sales=today_sales or 0,
            today_units=today_units or 0,
            waiting_shipment=sum(status_counts[s] for s in _BEFORE_SHIPMENT),
            top_products=[TopProduct(product_id=r[0], name=r[1], image_url=r[2], units=r[3]) for r in top_rows],
        )


def _with_lines(stmt):
    return stmt.options(selectinload(OrderModel.items).selectinload(OrderItemModel.product))


def _conditions(query: AdminOrderQuery, *, with_status: bool) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if with_status and query.status:
        conditions.append(OrderModel.status == query.status.value)
    if query.q:
        like = f"%{_escape_like(query.q)}%"
        options: list[ColumnElement[bool]] = [
            OrderModel.recipient.ilike(like, escape="\\"),
            OrderModel.phone.ilike(like, escape="\\"),
            exists().where(
                OrderItemModel.order_id == OrderModel.order_id,
                ProductModel.product_id == OrderItemModel.product_id,
                ProductModel.name.ilike(like, escape="\\"),
            ),
        ]
        # 주문번호는 정확히 일치. int4 범위를 넘는 숫자는 비교하지 않아요
        if query.q.isdigit() and len(query.q) <= 9:
            options.append(OrderModel.order_id == int(query.q))
        conditions.append(or_(*options))
    conditions.extend(_day_range(query.date_from, query.date_to))
    return conditions


def _day_range(date_from: date | None, date_to: date | None) -> list[ColumnElement[bool]]:
    # ordered_at 은 서버 시간(KST) 기준으로 저장돼요. 끝 날짜는 그날 하루 전체를 포함해요
    conditions: list[ColumnElement[bool]] = []
    if date_from:
        conditions.append(OrderModel.ordered_at >= datetime.combine(date_from, time.min))
    if date_to:
        conditions.append(OrderModel.ordered_at < datetime.combine(date_to + timedelta(days=1), time.min))
    return conditions


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_view(row: OrderModel, history: list[StatusChange] | None = None) -> AdminOrderView:
    return AdminOrderView(
        order_id=row.order_id,
        status=OrderStatus(row.status),
        ordered_at=row.ordered_at,
        total_price=row.total_price,
        buyer=BuyerView(
            name=row.recipient, phone=row.phone, zipcode=row.zipcode, address1=row.address1, address2=row.address2
        ),
        items=[
            OrderLineView(
                product_id=item.product_id,
                name=item.product.name,
                image_url=item.product.image_url,
                price=item.unit_price,
                quantity=item.quantity,
            )
            for item in row.items
        ],
        # orders 의 택배사 · 운송장 · 메모 컬럼은 SCRUM-35 리비전에서 추가돼요. 그 전에는 None
        courier=getattr(row, "courier", None),
        tracking_no=getattr(row, "tracking_no", None),
        admin_note=getattr(row, "admin_note", None),
        history=history,
    )


def _to_domain(row: OrderStatusHistoryModel) -> StatusChange:
    return StatusChange(
        from_status=OrderStatus(row.from_status) if row.from_status else None,
        to_status=OrderStatus(row.to_status),
        changed_at=row.changed_at,
        note=row.note,
        changed_by=row.changed_by,
    )
