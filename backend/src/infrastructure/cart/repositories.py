"""장바구니 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.cart.cart import Cart, CartLine
from infrastructure.auth.models import MemberModel
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

    async def lock_lines(self, member_id: int) -> list[tuple[int, int]]:
        """주문용: 장바구니 행을 잠그고 (상품 번호, 수량)을 상품 번호 순으로 돌려줘요.

        주문하는 동안 다른 탭에서 담기 · 수량 변경을 해도 주문이 끝날 때까지 기다려요.
        """
        rows = await self.session.execute(
            select(CartItemModel.product_id, CartItemModel.quantity)
            .where(CartItemModel.member_id == member_id)
            .order_by(CartItemModel.product_id)
            .with_for_update()
        )
        return [(pid, qty) for pid, qty in rows.all()]

    async def lock_member(self, member_id: int) -> None:
        """담기용: 회원 행을 잠가 같은 회원의 담기를 차례로 처리해요.

        처음 담는 상품은 잠글 장바구니 행이 아직 없어서, 동시에 두 번 담으면 둘 다 INSERT 하다 500 이 났어요 (SCRUM-69).
        """
        await self.session.execute(select(MemberModel.member_id).where(MemberModel.member_id == member_id).with_for_update())

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

    async def remove_products(self, member_id: int, product_ids: list[int]) -> None:
        """주문용: 주문한 상품만 빼요. 주문하는 사이 다른 탭에서 새로 담은 상품은 남아요 (SCRUM-69)."""
        await self.session.execute(
            delete(CartItemModel).where(CartItemModel.member_id == member_id, CartItemModel.product_id.in_(product_ids))
        )

    async def clear(self, member_id: int) -> None:
        await self.session.execute(delete(CartItemModel).where(CartItemModel.member_id == member_id))
