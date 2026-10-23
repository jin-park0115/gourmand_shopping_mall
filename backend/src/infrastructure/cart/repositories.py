"""장바구니 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.cart.cart import Cart, CartLine
from infrastructure.cart.models import CartItemModel
from infrastructure.product.repositories import ProductRepository


class CartRepository:
    """회원 한 명의 장바구니. 모든 조회 · 변경이 member_id 로 묶여서 남의 장바구니에는 닿지 않아요. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.products = ProductRepository(session)

    async def get_cart(self, member_id: int) -> Cart:
        rows = (
            await self.session.execute(
                select(CartItemModel.product_id, CartItemModel.quantity)
                .where(CartItemModel.member_id == member_id)
                .order_by(CartItemModel.added_at, CartItemModel.product_id)  # 먼저 담은 상품이 위
            )
        ).all()
        if not rows:
            return Cart(lines=[])
        listings, _ = await self.products.search(ids=[pid for pid, _ in rows], size=len(rows))
        product_of = {listing.product.id: listing.product for listing in listings}
        return Cart(lines=[CartLine(product_of[pid], qty) for pid, qty in rows if pid in product_of])

    async def get_quantity(self, member_id: int, product_id: int) -> int | None:
        """담겨 있지 않으면 None. 같은 상품을 동시에 담아도 합산이 꼬이지 않게 행을 잠가요."""
        return await self.session.scalar(
            select(CartItemModel.quantity)
            .where(CartItemModel.member_id == member_id, CartItemModel.product_id == product_id)
            .with_for_update()
        )

    async def save(self, member_id: int, product_id: int, quantity: int) -> None:
        row = await self.session.get(CartItemModel, (member_id, product_id))
        if row is None:
            self.session.add(CartItemModel(member_id=member_id, product_id=product_id, quantity=quantity))
        else:
            row.quantity = quantity
        await self.session.flush()

    async def remove(self, member_id: int, product_id: int) -> bool:
        """지웠으면 True, 원래 없었으면 False."""
        result = await self.session.execute(
            delete(CartItemModel).where(CartItemModel.member_id == member_id, CartItemModel.product_id == product_id)
        )
        return result.rowcount > 0

    async def clear(self, member_id: int) -> None:
        await self.session.execute(delete(CartItemModel).where(CartItemModel.member_id == member_id))
