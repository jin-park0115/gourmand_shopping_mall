"""관리자 주문 운영 요청·응답 Pydantic 스키마.

JSON 필드 이름은 camelCase (프론트 lib/orderStorage.ts 타입과 같게), 시간은 KST(+09:00)로 내보내요.
"""
from datetime import datetime, timedelta, timezone

from pydantic import field_serializer

from domain.admin.views import AdminOrderView, OrderSummary
from domain.admin.views import Page as ViewPage
from domain.order.status import OrderStatus, StatusChange
from presentation.schemas import CamelModel, Page

KST = timezone(timedelta(hours=9))


def _kst(value: datetime) -> str:
    # DB 의 ordered_at · changed_at 은 시간대 없이 KST 로 저장돼 있어요
    return (value if value.tzinfo else value.replace(tzinfo=KST)).isoformat()


class BuyerOut(CamelModel):
    buyer_name: str
    phone: str
    zipcode: str
    address1: str
    address2: str | None


class OrderLineOut(CamelModel):
    id: int
    name: str
    image_url: str
    price: int
    quantity: int


class HistoryOut(CamelModel):
    status: OrderStatus
    at: datetime
    note: str | None

    @field_serializer("at")
    def _at(self, value: datetime) -> str:
        return _kst(value)

    @classmethod
    def from_change(cls, change: StatusChange) -> "HistoryOut":
        return cls(status=change.to_status, at=change.changed_at, note=change.note)


class AdminOrderOut(CamelModel):
    order_id: int
    status: OrderStatus
    ordered_at: datetime
    total_price: int
    buyer: BuyerOut
    items: list[OrderLineOut]
    courier: str | None
    tracking_no: str | None
    admin_note: str | None
    next_statuses: list[OrderStatus]
    history: list[HistoryOut] | None = None

    @field_serializer("ordered_at")
    def _ordered_at(self, value: datetime) -> str:
        return _kst(value)

    @classmethod
    def from_view(cls, view: AdminOrderView) -> "AdminOrderOut":
        return cls(
            order_id=view.order_id,
            status=view.status,
            ordered_at=view.ordered_at,
            total_price=view.total_price,
            buyer=BuyerOut(
                buyer_name=view.buyer.name,
                phone=view.buyer.phone,
                zipcode=view.buyer.zipcode,
                address1=view.buyer.address1,
                address2=view.buyer.address2,
            ),
            items=[
                OrderLineOut(id=i.product_id, name=i.name, image_url=i.image_url, price=i.price, quantity=i.quantity)
                for i in view.items
            ],
            courier=view.courier,
            tracking_no=view.tracking_no,
            admin_note=view.admin_note,
            next_statuses=view.next_statuses,
            history=[HistoryOut.from_change(h) for h in view.history] if view.history is not None else None,
        )


def admin_order_page(page: ViewPage[AdminOrderView]) -> Page[AdminOrderOut]:
    """목록 응답: 공통 Page { items, total, page, size, pages } (presentation/schemas.py)."""
    return Page[AdminOrderOut].of(
        items=[AdminOrderOut.from_view(v) for v in page.items], total=page.total, page=page.page, size=page.size
    )

class TopProductOut(CamelModel):
    id: int
    name: str
    image_url: str
    units: int


class OrderSummaryOut(CamelModel):
    total: int
    status_counts: dict[str, int]
    today_orders: int
    today_sales: int
    today_units: int
    waiting_shipment: int
    top_products: list[TopProductOut]

    @classmethod
    def from_summary(cls, summary: OrderSummary) -> "OrderSummaryOut":
        return cls(
            total=summary.total,
            status_counts={s.value: n for s, n in summary.status_counts.items()},
            today_orders=summary.today_orders,
            today_sales=summary.today_sales,
            today_units=summary.today_units,
            waiting_shipment=summary.waiting_shipment,
            top_products=[
                TopProductOut(id=p.product_id, name=p.name, image_url=p.image_url, units=p.units)
                for p in summary.top_products
            ],
        )
