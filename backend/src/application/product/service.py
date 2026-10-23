"""상품 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import NotFoundError
from domain.product.product import CategorySummary, ProductListing, ProductSort
from infrastructure.product.repositories import ProductRepository


class ProductService:
    def __init__(self, session: AsyncSession):
        self.products = ProductRepository(session)

    async def search(
        self,
        *,
        q: str | None,
        country_slug: str | None,
        category_slug: str | None,
        ids: list[int] | None,
        sort: ProductSort,
        page: int,
        size: int,
    ) -> tuple[list[ProductListing], int]:
        return await self.products.search(
            q=q, country_slug=country_slug, category_slug=category_slug, ids=ids, sort=sort, page=page, size=size
        )

    async def get(self, product_id: int) -> ProductListing:
        listing = await self.products.get_listing(product_id)
        if listing is None:
            raise NotFoundError("상품을 찾을 수 없어요.")
        return listing

    async def categories(self) -> list[CategorySummary]:
        return await self.products.list_categories()
