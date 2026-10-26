"""DB 테스트용 데이터 만들기 도우미 (회원 · 상품 · 주문)."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.auth.models import MemberModel
from infrastructure.order.models import OrderItemModel, OrderModel
from infrastructure.product.models import CategoryModel, CountryModel, ProductModel


async def make_member(session: AsyncSession, *, email: str = "admin@test.com", role: str = "admin") -> MemberModel:
    member = MemberModel(email=email, password_hash="x", name="관리자" if role == "admin" else "고객", role=role)
    session.add(member)
    await session.flush()
    return member


async def make_product(session: AsyncSession, *, name: str = "로투스 비스코프", price: int = 4500, stock: int = 10) -> ProductModel:
    country = CountryModel(name=f"나라-{name}")
    category = CategoryModel(name=f"분류-{name}", slug=f"cat-{name}")
    product = ProductModel(
        country=country,
        category=category,
        name=name,
        manufacturer="제조사",
        description="설명",
        price=price,
        image_url=f"/images/{name}.png",
        stock=stock,
        delivery_days=3,
        volume=100,
        unit="g",
        origin="원산지",
        food_type="과자",
        storage_method="서늘한 곳",
    )
    session.add(product)
    await session.flush()
    return product


async def make_order(
    session: AsyncSession,
    member: MemberModel,
    lines: list[tuple[ProductModel, int]],
    *,
    status: str = "접수",
    recipient: str = "김구르",
    phone: str = "010-1234-5678",
    ordered_at: datetime | None = None,
) -> OrderModel:
    order = OrderModel(
        member_id=member.member_id,
        status=status,
        total_price=sum(p.price * qty for p, qty in lines),
        recipient=recipient,
        phone=phone,
        zipcode="06236",
        address1="서울 강남구 테헤란로 123",
        address2="4층",
        items=[OrderItemModel(product_id=p.product_id, quantity=qty, unit_price=p.price) for p, qty in lines],
    )
    if ordered_at is not None:
        order.ordered_at = ordered_at
    session.add(order)
    await session.flush()
    return order


async def deliver_all_products(session: AsyncSession, email: str) -> None:
    """리뷰 테스트용: 이 회원이 지금 있는 상품을 모두 배송완료로 받은 상태로 만들어요 (리뷰 작성 조건)."""
    member = await session.scalar(select(MemberModel).where(MemberModel.email == email))
    products = (await session.scalars(select(ProductModel))).all()
    await make_order(session, member, [(p, 1) for p in products], status="배송완료")
    await session.commit()
