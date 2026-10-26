"""주문 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.order.order import MyOrderQuery, Order, OrderLine, Payment, PaymentStatus, ShippingInfo
from domain.order.status import OrderStatus
from infrastructure.order.models import OrderItemModel, OrderModel, PaymentModel


class OrderRepository:
    """회원 본인 주문 저장 · 조회. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        member_id: int,
        shipping: ShippingInfo,
        lines: list[OrderLine],
        payment_method: str,
        ordered_at: datetime,
    ) -> int:
        """주문 · 주문 상품 · 결제(결제완료)를 저장하고 주문 번호를 돌려줘요."""
        total = sum(line.subtotal for line in lines)
        row = OrderModel(
            member_id=member_id,
            status=OrderStatus.RECEIVED.value,
            total_price=total,
            recipient=shipping.recipient,
            phone=shipping.phone,
            zipcode=shipping.zipcode,
            address1=shipping.address1,
            address2=shipping.address2,
            ordered_at=ordered_at,
            updated_at=ordered_at,
            items=[OrderItemModel(product_id=l.product_id, quantity=l.quantity, unit_price=l.unit_price) for l in lines],
            payment=PaymentModel(method=payment_method, amount=total, status=PaymentStatus.PAID.value, paid_at=ordered_at),
        )
        self.session.add(row)
        await self.session.flush()
        return row.order_id

    async def owner_of(self, order_id: int) -> int | None:
        """주문한 회원 번호. 없는 주문이면 None (404 와 남의 주문 403 을 구분하려고)."""
        return await self.session.scalar(select(OrderModel.member_id).where(OrderModel.order_id == order_id))

    async def has_delivered(self, member_id: int, product_id: int) -> bool:
        """이 회원의 배송완료 주문에 이 상품이 있는지 (리뷰 작성 조건)."""
        stmt = (
            select(OrderItemModel.order_item_id)
            .join(OrderModel, OrderModel.order_id == OrderItemModel.order_id)
            .where(
                OrderModel.member_id == member_id,
                OrderModel.status == OrderStatus.DELIVERED.value,
                OrderItemModel.product_id == product_id,
            )
            .limit(1)
        )
        return await self.session.scalar(stmt) is not None

    async def get(self, order_id: int) -> Order | None:
        row = await self.session.scalar(_with_details(select(OrderModel).where(OrderModel.order_id == order_id)))
        return _to_domain(row) if row else None

    async def search_mine(self, member_id: int, query: MyOrderQuery) -> tuple[list[Order], int]:
        """내 주문 (최근 주문이 먼저). (목록, 전체 개수)"""
        conditions = [OrderModel.member_id == member_id]
        if query.status:
            conditions.append(OrderModel.status == query.status.value)
        # ordered_at 은 KST 로 저장돼요. 끝 날짜는 그날 하루 전체를 포함해요 (관리자 목록과 같은 규칙)
        if query.date_from:
            conditions.append(OrderModel.ordered_at >= datetime.combine(query.date_from, time.min))
        if query.date_to:
            conditions.append(OrderModel.ordered_at < datetime.combine(query.date_to + timedelta(days=1), time.min))

        total = await self.session.scalar(select(func.count()).select_from(OrderModel).where(*conditions))
        rows = await self.session.scalars(
            _with_details(select(OrderModel).where(*conditions))
            .order_by(OrderModel.ordered_at.desc(), OrderModel.order_id.desc())
            .offset((query.page - 1) * query.size)
            .limit(query.size)
        )
        return [_to_domain(row) for row in rows], total or 0

    async def set_status(self, order_id: int, status: OrderStatus, changed_at: datetime) -> None:
        row = await self.session.get(OrderModel, order_id)
        row.status = status.value
        row.updated_at = changed_at
        await self.session.flush()


def _with_details(stmt):
    return stmt.options(
        selectinload(OrderModel.items).selectinload(OrderItemModel.product), selectinload(OrderModel.payment)
    ).execution_options(populate_existing=True)


def _to_domain(row: OrderModel) -> Order:
    payment = row.payment
    return Order(
        id=row.order_id,
        member_id=row.member_id,
        status=OrderStatus(row.status),
        ordered_at=row.ordered_at,
        shipping=ShippingInfo(row.recipient, row.phone, row.zipcode, row.address1, row.address2),
        lines=[
            OrderLine(item.product_id, item.product.name, item.product.image_url, item.unit_price, item.quantity)
            for item in sorted(row.items, key=lambda i: i.order_item_id)
        ],
        payment=Payment(payment.method, payment.amount, PaymentStatus(payment.status), payment.paid_at) if payment else None,
    )
