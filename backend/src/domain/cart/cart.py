"""장바구니 도메인 객체와 규칙 (순수 파이썬).

규칙: 수량 1개 ~ 재고, 품절 상품은 담을 수 없어요, 같은 상품을 다시 담으면 수량을 합쳐요.
가격은 담은 시점이 아니라 지금 판매가로 계산해요 (할인이 바뀌면 장바구니에도 바로 반영).
"""
from dataclasses import dataclass

from domain.exceptions import BusinessRuleError, InvalidValueError
from domain.product.product import Product


@dataclass(frozen=True)
class CartLine:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.product.sale_price * self.quantity


@dataclass(frozen=True)
class Cart:
    lines: list[CartLine]

    @property
    def total_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def total_price(self) -> int:
        return sum(line.subtotal for line in self.lines)


def check_cart_quantity(product: Product, quantity: int) -> None:
    """담거나 바꾼 뒤의 수량이 규칙에 맞는지 확인해요."""
    if quantity < 1:
        raise InvalidValueError("수량은 1개 이상이어야 해요.")
    if product.is_sold_out:
        raise BusinessRuleError(f"'{product.name}' 상품이 품절이에요.")
    if quantity > product.stock:
        raise BusinessRuleError(f"'{product.name}' 재고가 부족해요. (최대 {product.stock}개까지 담을 수 있어요)")
