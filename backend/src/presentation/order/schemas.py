"""주문 요청·응답 Pydantic 스키마."""
from datetime import datetime

from pydantic import Field

from domain.order.order import Order, OrderLine, Payment
from presentation.schemas import CamelModel


class OrderCreateIn(CamelModel):
    """배송 정보만 받아요. 주문 상품 · 가격은 서버 장바구니에서 가져와요. 형식 검사는 도메인(ShippingInfo)이 해요."""

    recipient: str = Field(max_length=50)
    phone: str = Field(max_length=20)
    zipcode: str = Field(max_length=10)
    address1: str = Field(max_length=200)
    address2: str | None = Field(None, max_length=200)


class OrderItemOut(CamelModel):
    product_id: int
    name: str
    image_url: str
    unit_price: int  # 주문 당시 판매가
    quantity: int
    subtotal: int

    @classmethod
    def of(cls, line: OrderLine) -> "OrderItemOut":
        return cls(**vars(line), subtotal=line.subtotal)


class PaymentOut(CamelModel):
    method: str
    amount: int
    status: str
    paid_at: datetime | None

    @classmethod
    def of(cls, payment: Payment) -> "PaymentOut":
        return cls(method=payment.method, amount=payment.amount, status=payment.status.value, paid_at=payment.paid_at)


class OrderOut(CamelModel):
    order_id: int
    status: str
    ordered_at: datetime  # KST (시간대 표시 없음)
    total_price: int
    recipient: str
    phone: str
    zipcode: str
    address1: str
    address2: str | None
    items: list[OrderItemOut]
    payment: PaymentOut | None

    @classmethod
    def of(cls, order: Order) -> "OrderOut":
        s = order.shipping
        return cls(
            order_id=order.id,
            status=order.status.value,
            ordered_at=order.ordered_at,
            total_price=order.total_price,
            recipient=s.recipient,
            phone=s.phone,
            zipcode=s.zipcode,
            address1=s.address1,
            address2=s.address2,
            items=[OrderItemOut.of(line) for line in order.lines],
            payment=PaymentOut.of(order.payment) if order.payment else None,
        )
