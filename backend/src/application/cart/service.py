"""장바구니 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from domain.cart.cart import Cart, check_cart_quantity
from domain.exceptions import NotFoundError
from domain.product.product import Product
from infrastructure.cart.repositories import CartRepository
from infrastructure.product.repositories import ProductRepository

NOT_IN_CART_MESSAGE = "장바구니에 없는 상품이에요."


class CartService:
    """모든 메서드가 바뀐 뒤의 장바구니 전체를 돌려줘요 (프론트가 응답으로 바로 화면을 갱신)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.carts = CartRepository(session)
        self.products = ProductRepository(session)

    async def get(self, member_id: int) -> Cart:
        return await self.carts.get_cart(member_id)

    async def add(self, member_id: int, product_id: int, quantity: int) -> Cart:
        """같은 상품이 이미 있으면 수량을 합쳐요. 합친 수량도 재고 이하여야 해요."""
        product = await self._product(product_id)
        current = await self.carts.get_quantity(member_id, product_id) or 0
        check_cart_quantity(product, current + quantity)
        await self.carts.save(member_id, product_id, current + quantity)
        await self.session.commit()
        return await self.get(member_id)

    async def set_quantity(self, member_id: int, product_id: int, quantity: int) -> Cart:
        if await self.carts.get_quantity(member_id, product_id) is None:
            raise NotFoundError(NOT_IN_CART_MESSAGE)
        check_cart_quantity(await self._product(product_id), quantity)
        await self.carts.save(member_id, product_id, quantity)
        await self.session.commit()
        return await self.get(member_id)

    async def remove(self, member_id: int, product_id: int) -> Cart:
        if not await self.carts.remove(member_id, product_id):
            raise NotFoundError(NOT_IN_CART_MESSAGE)
        await self.session.commit()
        return await self.get(member_id)

    async def clear(self, member_id: int) -> Cart:
        await self.carts.clear(member_id)
        await self.session.commit()
        return Cart(lines=[])

    async def _product(self, product_id: int) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise NotFoundError("상품을 찾을 수 없어요.")
        return product
