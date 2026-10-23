"""상품 도메인 객체와 규칙 (순수 파이썬).

규칙: 정가 ≥ 0, 할인가 ≤ 정가, 재고 ≥ 0. 재고가 0이면 품절이에요.
재고는 decrease_stock · increase_stock 으로만 바꿔요 (주문 생성 SCRUM-29 · 취소 SCRUM-35 에서 사용).
"""
from dataclasses import dataclass

from domain.exceptions import BusinessRuleError, InvalidValueError

OTHER_COUNTRY_SLUG = "other"  # 주요 4개국이 아닌 나라 (프론트 COUNTRY_FILTERS 의 "그 외")


@dataclass
class Product:
    id: int
    name: str
    price: int
    discount_price: int | None
    stock: int
    country: str
    country_slug: str
    category: str
    category_slug: str
    manufacturer: str
    description: str
    image_url: str
    is_new: bool
    delivery_days: int
    volume: float
    unit: str
    item_count: int
    origin: str
    food_type: str
    storage_method: str

    def __post_init__(self) -> None:
        if self.price < 0:
            raise InvalidValueError("정가는 0원 이상이어야 해요.")
        if self.discount_price is not None and not 0 <= self.discount_price <= self.price:
            raise InvalidValueError("할인가는 0원 이상, 정가 이하여야 해요.")
        if self.stock < 0:
            raise InvalidValueError("재고는 0개 이상이어야 해요.")

    @property
    def is_sold_out(self) -> bool:
        return self.stock == 0

    @property
    def has_discount(self) -> bool:
        # 할인가가 정가와 같으면 할인이 아니에요 (프론트 hasDiscount 와 같게)
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def sale_price(self) -> int:
        """실제로 결제하는 가격."""
        return self.discount_price if self.has_discount else self.price

    def decrease_stock(self, quantity: int) -> None:
        _check_quantity(quantity)
        if self.is_sold_out:
            raise BusinessRuleError(f"'{self.name}' 상품이 품절이에요.")
        if quantity > self.stock:
            raise BusinessRuleError(f"'{self.name}' 재고가 부족해요. (남은 수량 {self.stock}개)")
        self.stock -= quantity

    def increase_stock(self, quantity: int) -> None:
        _check_quantity(quantity)
        self.stock += quantity


def _check_quantity(quantity: int) -> None:
    if quantity < 1:
        raise InvalidValueError("수량은 1개 이상이어야 해요.")
