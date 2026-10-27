"""관리자 주문 운영 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import ColumnElement, exists, func, or_, select, update
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
from infrastructure.order.models import OrderItemModel, OrderModel, PaymentModel
from infrastructure.product.models import ProductModel

TOP_PRODUCT_LIMIT = 5
# payment.status 값: 결제완료 · 결제취소 (윤강 합의, SCRUM-29). 결제 쪽 값 정의는 B 영역이라 여기서는 상수 하나만 써요
PAYMENT_CANCELLED = "결제취소"
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


class AdminOrderCommandRepository:
    """관리자 상태 변경용 쓰기 작업. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock(self, order_id: int) -> OrderModel | None:
        # 같은 주문을 동시에 바꾸면 두 번째 요청은 첫 번째가 끝날 때까지 기다렸다가 바뀐 상태로 검사돼요
        return await self.session.scalar(
            select(OrderModel).where(OrderModel.order_id == order_id).with_for_update().execution_options(populate_existing=True)
        )

    async def cancel_payment(self, order_id: int) -> None:
        """주문의 결제 상태를 결제취소로 바꿔요. 결제 행이 없으면 아무것도 하지 않아요."""
        await self.session.execute(
            update(PaymentModel).where(PaymentModel.order_id == order_id).values(status=PAYMENT_CANCELLED)
        )

    async def quantities_by_product(self, order_id: int) -> list[tuple[int, int]]:
        """주문 상품별 수량 합계 (product_id 오름차순). 재고를 늘 같은 순서로 잠가서 데드락을 피해요."""
        rows = await self.session.execute(
            select(OrderItemModel.product_id, func.sum(OrderItemModel.quantity))
            .where(OrderItemModel.order_id == order_id)
            .group_by(OrderItemModel.product_id)
            .order_by(OrderItemModel.product_id)
        )
        return [(product_id, int(quantity)) for product_id, quantity in rows.all()]


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
            # 바깥 주문에만 묶어요. 요약 TOP 5 처럼 바깥이 상품 · 주문상품을 조인하면 자동 묶기로 FROM 이 비어 500 이 났어요
            exists().where(
                OrderItemModel.order_id == OrderModel.order_id,
                ProductModel.product_id == OrderItemModel.product_id,
                ProductModel.name.ilike(like, escape="\\"),
            ).correlate(OrderModel),
        ]
        # 연락처는 양쪽 하이픈을 빼고 비교해요: "01033334444" · "010-3333" 둘 다 "010-3333-4444" 를 찾고,
        # 하이픈만 있는 검색어("-")는 모든 연락처에 걸리지 않게 이 조건을 넣지 않아요
        digits = query.q.replace("-", "")
        if digits and any(c.isdecimal() for c in digits):
            options.append(func.replace(OrderModel.phone, "-", "").ilike(f"%{_escape_like(digits)}%", escape="\\"))
        # 주문번호는 정확히 일치. isdecimal 이라 '²' 같은 문자는 제외되고, int4 범위를 넘는 숫자는 비교하지 않아요
        if query.q.isdecimal() and len(query.q) <= 9:
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
            # relationship 에 순서가 없어서, 담긴 순서(order_item_id)로 고정해요
            for item in sorted(row.items, key=lambda i: i.order_item_id)
        ],
        courier=row.courier,
        tracking_no=row.tracking_no,
        admin_note=row.admin_note,
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
