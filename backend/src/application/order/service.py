"""주문 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from application.admin.service import now_kst  # DB 시간 컬럼은 시간대 없이 KST (관리자 화면 · 오늘 매출과 같은 기준)
from domain.exceptions import NotFoundError
from domain.order.order import DEMO_PAYMENT_METHOD, Order, ShippingInfo, take_stock_for_order
from domain.order.status import received
from domain.product.product import Product
from infrastructure.admin.repositories import OrderStatusHistoryRepository
from infrastructure.cart.repositories import CartRepository
from infrastructure.order.repositories import OrderRepository
from infrastructure.product.repositories import ProductRepository


class OrderService:
    def __init__(self, session: AsyncSession, *, now=now_kst):
        self.session = session
        self.orders = OrderRepository(session)
        self.carts = CartRepository(session)
        self.products = ProductRepository(session)
        self.history = OrderStatusHistoryRepository(session)
        self._now = now

    async def place_order(self, member_id: int, shipping: ShippingInfo) -> Order:
        """장바구니 → 주문. 재고 차감 · 주문 저장 · 결제완료 · 이력(접수) · 장바구니 비우기를 한 트랜잭션으로.

        재고가 하나라도 모자라면 이미 줄인 재고까지 전부 되돌리고 409 예요.
        """
        try:
            # 1. 장바구니를 잠그고 읽어요 (주문 중 다른 탭의 변경은 기다리게)
            cart_lines = await self.carts.lock_lines(member_id)

            # 2. 상품을 상품 번호 순서로 잠가요 (관리자 취소의 재고 복구와 같은 순서라 교착이 생기지 않아요)
            locked: list[tuple[Product, int]] = []
            for product_id, quantity in cart_lines:
                product = await self.products.get_for_update(product_id)
                if product is None:
                    raise NotFoundError(f"상품을 찾을 수 없어요. (상품 번호 {product_id})")
                locked.append((product, quantity))

            # 3. 도메인 규칙: 재고 차감 + 주문 당시 판매가로 주문 상품 만들기
            lines = take_stock_for_order(locked)
            for product, _ in locked:
                await self.products.save_stock(product)

            # 4. 주문 · 주문 상품 · 결제(결제완료) 저장 + 이력 첫 줄(없음 → 접수, SCRUM-33 합의)
            now = self._now()
            order_id = await self.orders.add(
                member_id=member_id, shipping=shipping, lines=lines, payment_method=DEMO_PAYMENT_METHOD, ordered_at=now
            )
            await self.history.add(order_id, received(changed_at=now))

            # 5. 장바구니 비우기
            await self.carts.clear(member_id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return await self.get_mine(member_id, order_id)

    async def get_mine(self, member_id: int, order_id: int) -> Order:
        order = await self.orders.get_mine(member_id, order_id)
        if order is None:
            raise NotFoundError("주문을 찾을 수 없어요.")
        return order
