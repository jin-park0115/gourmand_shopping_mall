"""주문 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from application.admin.service import now_kst  # DB 시간 컬럼은 시간대 없이 KST (관리자 화면 · 오늘 매출과 같은 기준)
from domain.exceptions import NotFoundError, PermissionDeniedError
from domain.order.order import DEMO_PAYMENT_METHOD, MyOrderQuery, Order, ShippingInfo, take_stock_for_order
from domain.order.status import OrderStatus, cancel_by_customer, received
from domain.product.product import Product
from infrastructure.admin.repositories import AdminOrderCommandRepository, OrderStatusHistoryRepository
from infrastructure.cart.repositories import CartRepository
from infrastructure.order.repositories import OrderRepository, SavedAddressRepository
from infrastructure.product.repositories import ProductRepository

NOT_FOUND_MESSAGE = "주문을 찾을 수 없어요."
NOT_MINE_MESSAGE = "본인 주문만 볼 수 있어요."


class OrderService:
    def __init__(self, session: AsyncSession, *, now=now_kst):
        self.session = session
        self.orders = OrderRepository(session)
        self.carts = CartRepository(session)
        self.products = ProductRepository(session)
        self.history = OrderStatusHistoryRepository(session)
        self.addresses = SavedAddressRepository(session)
        # 주문 잠금 · 상품별 수량 · 결제취소는 관리자 취소(C, SCRUM-35)와 같은 함수를 써요
        self.order_commands = AdminOrderCommandRepository(session)
        self._now = now

    async def place_order(self, member_id: int, shipping: ShippingInfo, *, save_address: bool = False) -> Order:
        """장바구니 → 주문. 재고 차감 · 주문 저장 · 결제완료 · 이력(접수) · 장바구니 비우기를 한 트랜잭션으로.
        save_address 면 이 배송 정보를 내 계정의 저장된 배송지로 (다음 주문서에서 불러와요).

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

            # 5. 장바구니 비우기 (+ 배송지 저장)
            await self.carts.clear(member_id)
            if save_address:
                await self.addresses.save(member_id, shipping)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return await self.get_mine(member_id, order_id)

    async def get_mine(self, member_id: int, order_id: int) -> Order:
        """없는 주문 404, 남의 주문 403 (Jira SCRUM-31 규칙)."""
        await self._check_owner(member_id, order_id)
        order = await self.orders.get(order_id)
        assert order is not None
        return order

    async def saved_address(self, member_id: int) -> ShippingInfo | None:
        return await self.addresses.get(member_id)

    async def list_mine(self, member_id: int, query: MyOrderQuery) -> tuple[list[Order], int]:
        return await self.orders.search_mine(member_id, query)

    async def cancel(self, member_id: int, order_id: int) -> Order:
        """고객 취소: 접수 · 상품준비중일 때만. 상태 · 이력 · 재고 복구 · 결제취소를 한 트랜잭션으로."""
        try:
            # 1. 주문 행을 잠그고 읽어요 (관리자가 동시에 출고 처리해도 한쪽이 끝난 뒤의 상태로 검사)
            row = await self.order_commands.lock(order_id)
            if row is None:
                raise NotFoundError(NOT_FOUND_MESSAGE)
            if row.member_id != member_id:
                raise PermissionDeniedError(NOT_MINE_MESSAGE)

            # 2. 도메인 규칙: 발송 전(접수 · 상품준비중)만 취소, 아니면 409
            now = self._now()
            change = cancel_by_customer(OrderStatus(row.status), changed_at=now)

            # 3. 상태 + 이력 (고객 취소는 changed_by 없음)
            await self.orders.set_status(order_id, change.to_status, now)
            await self.history.add(order_id, change)

            # 4. 재고 복구 (상품 번호 순서로 잠가서 주문 생성 · 관리자 취소와 교착이 생기지 않게) + 결제취소
            for product_id, quantity in await self.order_commands.quantities_by_product(order_id):
                product = await self.products.get_for_update(product_id)
                if product is None:
                    raise NotFoundError(f"상품을 찾을 수 없어요. (상품 번호 {product_id})")
                product.increase_stock(quantity)
                await self.products.save_stock(product)
            await self.order_commands.cancel_payment(order_id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return await self.get_mine(member_id, order_id)

    async def _check_owner(self, member_id: int, order_id: int) -> None:
        owner = await self.orders.owner_of(order_id)
        if owner is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        if owner != member_id:
            raise PermissionDeniedError(NOT_MINE_MESSAGE)
