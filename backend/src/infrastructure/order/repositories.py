"""주문 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.order.order import Order, OrderLine, Payment, PaymentStatus, ShippingInfo
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

    async def get_mine(self, member_id: int, order_id: int) -> Order | None:
        """남의 주문은 없는 주문과 똑같이 None (주문 번호로 남의 주문이 있는지 알 수 없게)."""
        row = await self.session.scalar(
            select(OrderModel)
            .where(OrderModel.order_id == order_id, OrderModel.member_id == member_id)
            .options(selectinload(OrderModel.items).selectinload(OrderItemModel.product), selectinload(OrderModel.payment))
        )
        return _to_domain(row) if row else None


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
