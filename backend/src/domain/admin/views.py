"""관리자 주문 화면용 조회 모델과 검색 조건 (순수 파이썬).

Repository 는 DB 행을 이 객체로 바꿔서 돌려주고, 표현 계층은 이 객체를 JSON 으로 바꿔요.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from math import ceil

from domain.exceptions import InvalidValueError
from domain.order.status import ADMIN_TRANSITIONS, OrderStatus, StatusChange

MAX_PAGE_SIZE = 100
MAX_QUERY_LENGTH = 50


@dataclass(frozen=True)
class AdminOrderQuery:
    """목록 · 요약 검색 조건. 만들 때 값 규칙을 검사해요."""

    status: OrderStatus | None = None
    q: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = 1
    size: int = 20

    def __post_init__(self) -> None:
        q = self.q.strip() if self.q and self.q.strip() else None
        object.__setattr__(self, "q", q)
        if q and len(q) > MAX_QUERY_LENGTH:
            raise InvalidValueError(f"검색어는 {MAX_QUERY_LENGTH}자 이하로 입력해 주세요.")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise InvalidValueError("시작일이 종료일보다 늦어요.")
        if self.page < 1:
            raise InvalidValueError("page는 1 이상이어야 해요.")
        if not 1 <= self.size <= MAX_PAGE_SIZE:
            raise InvalidValueError(f"size는 1~{MAX_PAGE_SIZE} 사이여야 해요.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


@dataclass(frozen=True)
class BuyerView:
    name: str
    phone: str
    zipcode: str
    address1: str
    address2: str | None


@dataclass(frozen=True)
class OrderLineView:
    product_id: int
    name: str
    image_url: str
    price: int  # 주문 당시 가격 (order_item.unit_price)
    quantity: int


@dataclass(frozen=True)
class AdminOrderView:
    order_id: int
    status: OrderStatus
    ordered_at: datetime
    total_price: int
    buyer: BuyerView
    items: list[OrderLineView]
    courier: str | None = None
    tracking_no: str | None = None
    admin_note: str | None = None
    history: list[StatusChange] | None = None  # 상세 · 상태 변경 응답에서만 채워요

    @property
    def next_statuses(self) -> list[OrderStatus]:
        # 화면 버튼 순서가 늘 같도록 상태 정의 순서로 정렬해요
        allowed = ADMIN_TRANSITIONS[self.status]
        return [s for s in OrderStatus if s in allowed]


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size) if self.total else 0


@dataclass(frozen=True)
class TopProduct:
    product_id: int
    name: str
    image_url: str
    units: int


@dataclass(frozen=True)
class OrderSummary:
    total: int
    status_counts: dict[OrderStatus, int]
    today_orders: int
    today_sales: int
    today_units: int
    waiting_shipment: int
    top_products: list[TopProduct] = field(default_factory=list)
