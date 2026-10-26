"""주문 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.order.service import OrderService
from database import get_session
from domain.auth.member import CurrentUser
from domain.order.order import ShippingInfo
from presentation.auth.dependencies import get_current_user
from presentation.order.schemas import OrderCreateIn, OrderOut

router = APIRouter(prefix="/orders", tags=["order"])


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(session)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order(
    body: OrderCreateIn,
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    """내 장바구니 전체를 주문해요. 성공하면 장바구니는 비워져요."""
    shipping = ShippingInfo.of(
        recipient=body.recipient, phone=body.phone, zipcode=body.zipcode, address1=body.address1, address2=body.address2
    )
    return OrderOut.of(await service.place_order(user.member_id, shipping))


@router.get("/{order_id}", response_model=OrderOut)
async def get_my_order(
    order_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    """내 주문 하나 (주문 완료 화면용). 남의 주문은 404."""
    return OrderOut.of(await service.get_mine(user.member_id, order_id))
