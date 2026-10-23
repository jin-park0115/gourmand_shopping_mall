"""상품 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from domain.product.product import OTHER_COUNTRY_SLUG, Product
from infrastructure.product.models import ProductModel


class ProductRepository:
    """상품 조회 · 재고 저장. commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, product_id: int) -> Product | None:
        row = await self.session.scalar(_select_product(product_id))
        return _to_domain(row) if row else None

    async def get_for_update(self, product_id: int) -> Product | None:
        """행을 잠그고 읽어요 (SELECT … FOR UPDATE). 주문 · 취소처럼 재고를 바꾸기 전에 써요.

        트랜잭션이 끝날 때까지 다른 요청은 같은 상품을 기다려서, 동시에 주문해도 재고가 음수가 되지 않아요.
        """
        row = await self.session.scalar(_select_product(product_id).with_for_update(of=ProductModel))
        return _to_domain(row) if row else None

    async def save_stock(self, product: Product) -> None:
        """도메인에서 바꾼 재고를 DB에 반영해요. 상품 정보 수정은 이번 범위가 아니라 재고만 써요."""
        row = await self.session.get(ProductModel, product.id)
        row.stock = product.stock
        await self.session.flush()


def _select_product(product_id: int):
    return (
        select(ProductModel)
        .where(ProductModel.product_id == product_id)
        .options(joinedload(ProductModel.country, innerjoin=True), joinedload(ProductModel.category, innerjoin=True))
    )


def _to_domain(row: ProductModel) -> Product:
    return Product(
        id=row.product_id,
        name=row.name,
        price=row.price,
        discount_price=row.discount_price,
        stock=row.stock,
        country=row.country.name,
        country_slug=row.country.slug or OTHER_COUNTRY_SLUG,
        category=row.category.name,
        category_slug=row.category.slug,
        manufacturer=row.manufacturer,
        description=row.description,
        image_url=row.image_url,
        is_new=row.is_new,
        delivery_days=row.delivery_days,
        volume=row.volume,
        unit=row.unit,
        item_count=row.item_count,
        origin=row.origin,
        food_type=row.food_type,
        storage_method=row.storage_method,
    )
