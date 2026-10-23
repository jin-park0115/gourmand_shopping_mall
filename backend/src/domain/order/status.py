"""주문 상태와 상태 전이 규칙 (순수 파이썬).

Order 클래스(B 담당)는 상태를 바꿀 때 이 모듈의 함수로 검사만 맡기면 돼요.
그래서 Order 파일을 같이 고치지 않아도 되고, 규칙은 한 곳에서만 관리돼요.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from domain.exceptions import BusinessRuleError, InvalidValueError


class OrderStatus(StrEnum):
    """값은 프론트(lib/orderStorage.ts ORDER_STATUSES)와 같은 한글 문자열이에요."""

    RECEIVED = "접수"
    PREPARING = "상품준비중"
    SHIPPING = "배송중"
    DELIVERED = "배송완료"
    DELAYED = "배송지연"
    CANCELLED = "주문취소"


# 관리자가 바꿀 수 있는 상태: 현재 상태 → 다음 상태들
ADMIN_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.RECEIVED: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
    OrderStatus.PREPARING: frozenset({OrderStatus.SHIPPING, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPING: frozenset({OrderStatus.DELIVERED, OrderStatus.DELAYED}),
    OrderStatus.DELAYED: frozenset({OrderStatus.SHIPPING, OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# 고객이 직접 취소할 수 있는 상태 (발송 전까지만)
CUSTOMER_CANCELLABLE: frozenset[OrderStatus] = frozenset({OrderStatus.RECEIVED, OrderStatus.PREPARING})

# 관리자 화면의 택배사 선택지와 같아요
COURIERS: tuple[str, ...] = ("CJ대한통운", "우체국택배", "한진택배", "롯데택배")
TRACKING_NO_PATTERN = re.compile(r"^[0-9-]{8,20}$")


@dataclass(frozen=True)
class StatusChange:
    """상태가 한 번 바뀐 기록. order_status_history 한 줄에 해당해요."""

    from_status: OrderStatus | None  # 주문이 처음 만들어질 때(접수)는 None
    to_status: OrderStatus
    changed_at: datetime
    note: str | None = None
    changed_by: int | None = None  # 바꾼 관리자 id, 고객 취소는 None
    courier: str | None = None  # 처음 배송중으로 바꿀 때만 채워져요
    tracking_no: str | None = None

    @property
    def restores_stock(self) -> bool:
        # 취소되면 주문 수량만큼 재고를 되돌려야 해요 (같은 트랜잭션에서 처리)
        return self.to_status is OrderStatus.CANCELLED


def parse_status(value: str) -> OrderStatus:
    try:
        return OrderStatus(value)
    except ValueError:
        allowed = ", ".join(s.value for s in OrderStatus)
        raise InvalidValueError(f"알 수 없는 주문 상태예요: {value} (가능한 값: {allowed})") from None


def change_by_admin(
    current: OrderStatus,
    target: OrderStatus,
    *,
    changed_at: datetime,
    changed_by: int | None = None,
    courier: str | None = None,
    tracking_no: str | None = None,
    note: str | None = None,
) -> StatusChange:
    """관리자 상태 변경 규칙을 검사하고, 통과하면 이력 한 줄을 돌려줘요."""
    if current is target:
        raise BusinessRuleError(f"이미 '{current}' 상태예요.")
    if target not in ADMIN_TRANSITIONS[current]:
        raise BusinessRuleError(f"'{current}' 상태에서 '{target}'(으)로 바꿀 수 없어요.")
    note = note.strip() if note and note.strip() else None
    if target in (OrderStatus.DELAYED, OrderStatus.CANCELLED) and note is None:
        raise InvalidValueError(f"'{target}'(으)로 바꾸려면 사유를 입력해 주세요.")

    # 처음 출고(상품준비중 → 배송중)할 때만 운송장을 받아요. 배송지연 → 배송중은 이미 등록된 운송장을 그대로 써요
    shipping = None
    if target is OrderStatus.SHIPPING and current is OrderStatus.PREPARING:
        shipping = _validated_shipping(courier, tracking_no)
    return StatusChange(
        from_status=current,
        to_status=target,
        changed_at=changed_at,
        note=note,
        changed_by=changed_by,
        courier=shipping[0] if shipping else None,
        tracking_no=shipping[1] if shipping else None,
    )


def received(*, changed_at: datetime) -> StatusChange:
    """주문이 처음 만들어질 때의 이력 첫 줄 (없음 → 접수). 주문 생성(B)에서 같이 저장해요."""
    return StatusChange(from_status=None, to_status=OrderStatus.RECEIVED, changed_at=changed_at)


def cancel_by_customer(current: OrderStatus, *, changed_at: datetime) -> StatusChange:
    """고객 취소는 접수 · 상품준비중일 때만 가능해요."""
    if current not in CUSTOMER_CANCELLABLE:
        raise BusinessRuleError(f"'{current}' 상태의 주문은 취소할 수 없어요. 고객센터에 문의해 주세요.")
    return StatusChange(from_status=current, to_status=OrderStatus.CANCELLED, changed_at=changed_at)


def _validated_shipping(courier: str | None, tracking_no: str | None) -> tuple[str, str]:
    courier = (courier or "").strip()
    tracking_no = (tracking_no or "").strip()
    if not courier or not tracking_no:
        raise InvalidValueError("배송중으로 바꾸려면 택배사와 운송장 번호가 필요해요.")
    if courier not in COURIERS:
        raise InvalidValueError(f"지원하지 않는 택배사예요. ({', '.join(COURIERS)} 중에서 골라 주세요)")
    if not TRACKING_NO_PATTERN.fullmatch(tracking_no):
        raise InvalidValueError("운송장 번호는 숫자와 '-'로 8~20자여야 해요.")
    return courier, tracking_no
