"""장바구니 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환.

모든 API 가 로그인한 회원 본인의 장바구니만 다뤄요 (경로에 회원 번호가 없어요).
"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from application.cart.service import CartService
from database import get_session
from domain.auth.member import CurrentUser
from presentation.auth.dependencies import get_current_user, require_customer
from presentation.cart.schemas import CartAddIn, CartOut, CartQuantityIn

router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_service(session: AsyncSession = Depends(get_session)) -> CartService:
    return CartService(session)


@router.get("", response_model=CartOut)
async def get_cart(
    user: CurrentUser = Depends(get_current_user), service: CartService = Depends(get_cart_service)
) -> CartOut:
    return CartOut.of(await service.get(user.member_id))


@router.post("/items", response_model=CartOut)
async def add_item(
    body: CartAddIn, user: CurrentUser = Depends(require_customer), service: CartService = Depends(get_cart_service)
) -> CartOut:
    """같은 상품을 다시 담으면 수량을 합쳐요. 관리자 계정은 403."""
    return CartOut.of(await service.add(user.member_id, body.product_id, body.quantity))


@router.patch("/items/{product_id}", response_model=CartOut)
async def set_quantity(
    body: CartQuantityIn,
    product_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    return CartOut.of(await service.set_quantity(user.member_id, product_id, body.quantity))


@router.delete("/items/{product_id}", response_model=CartOut)
async def remove_item(
    product_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    return CartOut.of(await service.remove(user.member_id, product_id))


@router.delete("", response_model=CartOut)
async def clear_cart(
    user: CurrentUser = Depends(get_current_user), service: CartService = Depends(get_cart_service)
) -> CartOut:
    return CartOut.of(await service.clear(user.member_id))
