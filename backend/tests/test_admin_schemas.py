"""SCRUM-34: 관리자 주문 응답 JSON 이 docs/API.md 모양(camelCase, KST 시간)인지 검사합니다."""
from datetime import datetime

from domain.admin.views import AdminOrderView, BuyerView, OrderLineView, OrderSummary, Page, TopProduct
from domain.order.status import OrderStatus, received
from presentation.admin.schemas import AdminOrderOut, AdminOrderPageOut, OrderSummaryOut

VIEW = AdminOrderView(
    order_id=17,
    status=OrderStatus.SHIPPING,
    ordered_at=datetime(2026, 10, 23, 14, 5),
    total_price=27800,
    buyer=BuyerView(name="김구르", phone="010-1234-5678", zipcode="06236", address1="서울 강남구", address2="4층"),
    items=[OrderLineView(product_id=3, name="로투스 비스코프", image_url="/lotus.jpg", price=4500, quantity=2)],
    courier="CJ대한통운",
    tracking_no="1234-5678-9012",
    history=[received(changed_at=datetime(2026, 10, 23, 14, 5))],
)


def test_admin_order_json_shape() -> None:
    data = AdminOrderOut.from_view(VIEW).model_dump(mode="json")
    assert data["orderId"] == 17
    assert data["orderedAt"] == "2026-10-23T14:05:00+09:00"
    assert data["buyer"] == {"buyerName": "김구르", "phone": "010-1234-5678", "zipcode": "06236", "address1": "서울 강남구", "address2": "4층"}
    assert data["items"] == [{"id": 3, "name": "로투스 비스코프", "imageUrl": "/lotus.jpg", "price": 4500, "quantity": 2}]
    assert (data["courier"], data["trackingNo"], data["adminNote"]) == ("CJ대한통운", "1234-5678-9012", None)
    assert data["nextStatuses"] == ["배송완료", "배송지연"]
    assert data["history"] == [{"status": "접수", "at": "2026-10-23T14:05:00+09:00", "note": None}]


def test_page_json_shape() -> None:
    list_view = AdminOrderView(**{**VIEW.__dict__, "history": None})
    data = AdminOrderPageOut.from_page(Page(items=[list_view], total=41, page=2, size=20)).model_dump(mode="json")
    assert (data["total"], data["page"], data["size"], data["pages"]) == (41, 2, 20, 3)
    assert data["items"][0]["history"] is None


def test_summary_json_shape() -> None:
    summary = OrderSummary(
        total=3,
        status_counts={s: 0 for s in OrderStatus} | {OrderStatus.RECEIVED: 3},
        today_orders=1,
        today_sales=9000,
        today_units=2,
        waiting_shipment=3,
        top_products=[TopProduct(product_id=3, name="로투스", image_url="/l.jpg", units=7)],
    )
    data = OrderSummaryOut.from_summary(summary).model_dump(mode="json")
    assert data["statusCounts"]["접수"] == 3 and data["statusCounts"]["주문취소"] == 0
    assert data["todaySales"] == 9000 and data["waitingShipment"] == 3
    assert data["topProducts"] == [{"id": 3, "name": "로투스", "imageUrl": "/l.jpg", "units": 7}]
