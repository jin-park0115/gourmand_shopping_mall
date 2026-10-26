"""SCRUM-21: 상품 도메인 규칙 (순수 파이썬)."""
from dataclasses import replace

import pytest

from domain.exceptions import BusinessRuleError, InvalidValueError
from domain.product.product import Product

BASE = dict(
    id=3, name="곤약젤리", price=4500, discount_price=3900, stock=5,
    country="일본", country_slug="japan", category="젤리·캔디", category_slug="candy",
    manufacturer="오리히로", description="설명", image_url="/3.webp", is_new=False, delivery_days=3,
    volume=25, unit="g", item_count=12, origin="일본", food_type="젤리", storage_method="서늘한 곳",
)


def make(**changes) -> Product:
    return Product(**{**BASE, **changes})


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"price": -1}, "정가"),
        ({"discount_price": 4501}, "할인가"),
        ({"discount_price": -1}, "할인가"),
        ({"stock": -1}, "재고"),
    ],
)
def test_invalid_values_are_rejected(changes, message) -> None:
    with pytest.raises(InvalidValueError, match=message):
        make(**changes)


def test_sale_price_and_discount() -> None:
    assert make().sale_price == 3900 and make().has_discount
    assert make(discount_price=None).sale_price == 4500
    same = make(discount_price=4500)  # 정가와 같은 할인가는 허용하지만 할인은 아니에요
    assert not same.has_discount and same.sale_price == 4500


def test_sold_out_when_stock_is_zero() -> None:
    assert make(stock=0).is_sold_out and not make(stock=1).is_sold_out


def test_decrease_and_increase_stock() -> None:
    p = make(stock=5)
    p.decrease_stock(5)
    assert p.stock == 0 and p.is_sold_out
    p.increase_stock(2)
    assert p.stock == 2


@pytest.mark.parametrize("stock, quantity, error", [(3, 4, "재고가 부족"), (0, 1, "품절")])
def test_cannot_decrease_more_than_stock(stock, quantity, error) -> None:
    p = make(stock=stock)
    with pytest.raises(BusinessRuleError, match=error):
        p.decrease_stock(quantity)
    assert p.stock == stock  # 실패하면 재고는 그대로


@pytest.mark.parametrize("method", ["decrease_stock", "increase_stock"])
def test_quantity_must_be_positive(method) -> None:
    with pytest.raises(InvalidValueError, match="수량"):
        getattr(make(), method)(0)
