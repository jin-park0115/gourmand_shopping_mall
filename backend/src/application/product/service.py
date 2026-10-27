"""상품 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import NotFoundError
from domain.product.product import CategorySummary, ProductListing, ProductSort
from domain.product.search import SearchQuery
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

    async def suggest(self, q: str, *, limit: int) -> tuple[list[ProductListing], int, list[CategorySummary], list[tuple[str, str]]]:
        """검색창 자동완성: (추천순 상품 limit 개, 전체 개수, 이름이 맞는 카테고리, 이름이 맞는 나라)."""
        query = SearchQuery(q)
        if not query:
            return [], 0, [], []
        listings, total = await self.products.search(q=q, sort=ProductSort.RECOMMEND, page=1, size=limit)
        categories = [c for c in await self.products.list_categories() if query.matches_name(c.name)]
        countries = [(name, slug) for name, slug in await self.products.list_countries() if query.matches_name(name)]
        return listings, total, categories, countries
