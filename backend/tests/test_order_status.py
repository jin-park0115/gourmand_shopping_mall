"""SCRUM-32: 주문 상태 전이 규칙을 허용/불허 조합 전부 검사합니다."""
from datetime import datetime
from itertools import product

import pytest

from domain.exceptions import BusinessRuleError, InvalidValueError
from domain.order.status import (
    ADMIN_TRANSITIONS,
    OrderStatus,
    cancel_by_customer,
    change_by_admin,
    parse_status,
)

S = OrderStatus
NOW = datetime(2026, 10, 23, 12, 0)

ALLOWED = [
    (S.RECEIVED, S.PREPARING),
    (S.RECEIVED, S.CANCELLED),
    (S.PREPARING, S.SHIPPING),
    (S.PREPARING, S.CANCELLED),
    (S.SHIPPING, S.DELIVERED),
    (S.SHIPPING, S.DELAYED),
    (S.DELAYED, S.SHIPPING),
    (S.DELAYED, S.DELIVERED),
]
NOT_ALLOWED = [(a, b) for a, b in product(S, S) if a is not b and (a, b) not in ALLOWED]


def _shipping_info(target: OrderStatus) -> dict:
    return {"courier": "CJ대한통운", "tracking_no": "1234567890"} if target is S.SHIPPING else {}


def test_transition_table_matches_spec() -> None:
    table = {(a, b) for a, nexts in ADMIN_TRANSITIONS.items() for b in nexts}
    assert table == set(ALLOWED)


@pytest.mark.parametrize(("current", "target"), ALLOWED)
def test_allowed_admin_transitions(current: OrderStatus, target: OrderStatus) -> None:
    change = change_by_admin(current, target, changed_at=NOW, **_shipping_info(target))
    assert (change.from_status, change.to_status, change.changed_at) == (current, target, NOW)


@pytest.mark.parametrize(("current", "target"), NOT_ALLOWED)
def test_not_allowed_admin_transitions(current: OrderStatus, target: OrderStatus) -> None:
    with pytest.raises(BusinessRuleError):
        change_by_admin(current, target, changed_at=NOW, **_shipping_info(target))


@pytest.mark.parametrize("status", list(S))
def test_same_status_is_rejected(status: OrderStatus) -> None:
    with pytest.raises(BusinessRuleError, match="이미"):
        change_by_admin(status, status, changed_at=NOW)


@pytest.mark.parametrize(
    ("courier", "tracking_no"),
    [(None, None), ("CJ대한통운", None), (None, "123"), ("  ", "123"), ("CJ대한통운", "")],
)
@pytest.mark.parametrize("current", [S.PREPARING, S.DELAYED])
def test_shipping_requires_courier_and_tracking(current: OrderStatus, courier, tracking_no) -> None:
    with pytest.raises(InvalidValueError, match="운송장"):
        change_by_admin(current, S.SHIPPING, changed_at=NOW, courier=courier, tracking_no=tracking_no)


def test_cancel_restores_stock_and_others_do_not() -> None:
    assert change_by_admin(S.PREPARING, S.CANCELLED, changed_at=NOW).restores_stock
    assert not change_by_admin(S.RECEIVED, S.PREPARING, changed_at=NOW).restores_stock


def test_note_is_kept_in_history() -> None:
    change = change_by_admin(S.SHIPPING, S.DELAYED, changed_at=NOW, note="태풍으로 지연")
    assert change.note == "태풍으로 지연"


@pytest.mark.parametrize("current", [S.RECEIVED, S.PREPARING])
def test_customer_can_cancel_before_shipping(current: OrderStatus) -> None:
    change = cancel_by_customer(current, changed_at=NOW)
    assert change.to_status is S.CANCELLED
    assert change.restores_stock


@pytest.mark.parametrize("current", [S.SHIPPING, S.DELAYED, S.DELIVERED, S.CANCELLED])
def test_customer_cannot_cancel_after_shipping(current: OrderStatus) -> None:
    with pytest.raises(BusinessRuleError):
        cancel_by_customer(current, changed_at=NOW)


def test_parse_status() -> None:
    assert parse_status("배송중") is S.SHIPPING
    with pytest.raises(InvalidValueError, match="알 수 없는"):
        parse_status("반품")


def test_status_values_match_frontend() -> None:
    # gourmand/lib/orderStorage.ts 의 ORDER_STATUSES 와 순서까지 같아야 화면 필터가 그대로 동작해요
    assert [s.value for s in S] == ["접수", "상품준비중", "배송중", "배송완료", "배송지연", "주문취소"]
