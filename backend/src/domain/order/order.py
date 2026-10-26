"""주문 도메인 객체와 생성 규칙 (순수 파이썬).

규칙: 주문 상품은 서버 장바구니에서 가져와요 (요청으로 가격 · 수량을 받지 않아요).
가격은 주문하는 순간의 판매가로 고정해요 (order_item.unit_price). 재고가 하나라도 모자라면 주문 전체가 취소돼요.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from domain.exceptions import BusinessRuleError, InvalidValueError
from domain.order.status import OrderStatus
from domain.product.product import Product

PHONE_PATTERN = re.compile(r"^01[0-9]-?\d{3,4}-?\d{4}$")  # 프론트 CheckoutForm 과 같은 규칙
ZIPCODE_PATTERN = re.compile(r"^\d{5}$")
DEMO_PAYMENT_METHOD = "카드"  # 실제 결제 연동이 없어서 주문하면 바로 결제완료로 저장해요 (시연용)


class PaymentStatus(StrEnum):
    """payment.status 값 (C 와 합의: 주문하면 결제완료, 취소하면 결제취소)."""

    PAID = "결제완료"
    CANCELLED = "결제취소"


@dataclass(frozen=True)
class ShippingInfo:
    recipient: str
    phone: str
    zipcode: str
    address1: str
    address2: str | None = None

    @classmethod
    def of(cls, *, recipient: str, phone: str, zipcode: str, address1: str, address2: str | None) -> "ShippingInfo":
        recipient, phone, zipcode, address1 = recipient.strip(), phone.strip(), zipcode.strip(), address1.strip()
        address2 = address2.strip() if address2 and address2.strip() else None
        if not recipient:
            raise InvalidValueError("받는 분 이름을 입력해 주세요.")
        if not PHONE_PATTERN.fullmatch(phone):
            raise InvalidValueError("휴대폰 번호를 올바르게 입력해 주세요. (예: 010-1234-5678)")
        if not ZIPCODE_PATTERN.fullmatch(zipcode):
            raise InvalidValueError("우편번호 5자리를 입력해 주세요.")
        if not address1:
            raise InvalidValueError("주소를 입력해 주세요.")
        return cls(recipient, phone, zipcode, address1, address2)


@dataclass(frozen=True)
class OrderLine:
    product_id: int
    name: str
    image_url: str
    unit_price: int  # 주문 당시 판매가
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class Payment:
    method: str
    amount: int
    status: PaymentStatus
    paid_at: datetime | None


@dataclass(frozen=True)
class Order:
    id: int
    member_id: int
    status: OrderStatus
    ordered_at: datetime
    shipping: ShippingInfo
    lines: list[OrderLine]
    payment: Payment | None

    @property
    def total_price(self) -> int:
        return sum(line.subtotal for line in self.lines)


def take_stock_for_order(locked: list[tuple[Product, int]]) -> list[OrderLine]:
    """잠근 상품마다 재고를 줄이고 주문 상품을 만들어요. 하나라도 모자라면 BusinessRuleError (호출한 쪽이 전체 롤백)."""
    if not locked:
        raise BusinessRuleError("장바구니가 비어 있어요.")
    lines = []
    for product, quantity in locked:
        product.decrease_stock(quantity)  # 품절 · 재고 부족이면 여기서 예외
        lines.append(OrderLine(product.id, product.name, product.image_url, product.sale_price, quantity))
    return lines
