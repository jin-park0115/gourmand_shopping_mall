"""장바구니 요청·응답 Pydantic 스키마."""
from pydantic import Field

from domain.cart.cart import Cart, CartLine
from presentation.schemas import CamelModel

MAX_QUANTITY = 999  # 요청 값 상한 (실제 상한은 재고)


class CartAddIn(CamelModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(1, ge=1, le=MAX_QUANTITY)


class CartQuantityIn(CamelModel):
    quantity: int = Field(ge=1, le=MAX_QUANTITY)


class CartItemOut(CamelModel):
    """프론트 components/CartProvider.tsx 의 CartItem 과 같은 모양 (+ isSoldOut · subtotal)."""

    id: int  # 상품 번호
    name: str
    image_url: str
    price: int  # 지금 판매가 (할인가가 있으면 할인가)
    quantity: int
    stock: int
    is_sold_out: bool  # 담아 둔 사이 품절되면 true → 화면에서 주문 전에 빼도록 안내
    subtotal: int

    @classmethod
    def of(cls, line: CartLine) -> "CartItemOut":
        p = line.product
        return cls(
            id=p.id,
            name=p.name,
            image_url=p.image_url,
            price=p.sale_price,
            quantity=line.quantity,
            stock=p.stock,
            is_sold_out=p.is_sold_out,
            subtotal=line.subtotal,
        )


class CartOut(CamelModel):
    items: list[CartItemOut]
    total_count: int
    total_price: int

    @classmethod
    def of(cls, cart: Cart) -> "CartOut":
        return cls(
            items=[CartItemOut.of(line) for line in cart.lines],
            total_count=cart.total_count,
            total_price=cart.total_price,
        )
