"""주문 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.order.service import OrderService
from database import get_session
from domain.auth.member import CurrentUser
from domain.order.order import MAX_PAGE_SIZE, MyOrderQuery, ShippingInfo
from domain.order.status import OrderStatus
from presentation.auth.dependencies import get_current_user, require_customer
from presentation.order.schemas import OrderCreateIn, OrderOut, ShippingOut
from presentation.schemas import Page

router = APIRouter(prefix="/orders", tags=["order"])


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(session)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order(
    body: OrderCreateIn,
    user: CurrentUser = Depends(require_customer),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    """내 장바구니 전체를 주문해요. 성공하면 장바구니는 비워져요. 관리자 계정은 403."""
    shipping = ShippingInfo.of(
        recipient=body.recipient, phone=body.phone, zipcode=body.zipcode, address1=body.address1, address2=body.address2
    )
    return OrderOut.of(
        await service.place_order(
            user.member_id, shipping, save_address=body.save_address, expected_total=body.expected_total_price
        )
    )


@router.get("", response_model=Page[OrderOut])
async def list_my_orders(
    order_status: OrderStatus | None = Query(None, alias="status", description="6개 주문 상태 중 하나"),
    date_from: date | None = Query(None, alias="from", description="주문일 시작 YYYY-MM-DD (KST)"),
    date_to: date | None = Query(None, alias="to", description="주문일 끝 YYYY-MM-DD (그날 포함)"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=MAX_PAGE_SIZE),
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> Page[OrderOut]:
    """내 주문 목록 (최근 주문이 먼저)."""
    query = MyOrderQuery(status=order_status, date_from=date_from, date_to=date_to, page=page, size=size)
    orders, total = await service.list_mine(user.member_id, query)
    return Page.of([OrderOut.of(o) for o in orders], total, page, size)


@router.get("/saved-address", response_model=ShippingOut | None)
async def my_saved_address(
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ShippingOut | None:
    """내 계정에 저장된 배송지 (주문할 때 '저장'을 고른 마지막 배송 정보). 없으면 null."""
    saved = await service.saved_address(user.member_id)
    return ShippingOut.of(saved) if saved else None


@router.get("/{order_id}", response_model=OrderOut)
async def get_my_order(
    order_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    """내 주문 하나 (주문 완료 화면용). 없는 주문 404, 남의 주문 403."""
    return OrderOut.of(await service.get_mine(user.member_id, order_id))


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_my_order(
    order_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    """고객 취소: 접수 · 상품준비중일 때만 (그 뒤는 409). 재고를 되돌리고 결제는 결제취소로."""
    return OrderOut.of(await service.cancel(user.member_id, order_id))
