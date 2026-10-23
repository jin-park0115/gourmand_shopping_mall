"""상품 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
import re

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from domain.product.product import (
    OTHER_COUNTRY_SLUG,
    CategorySummary,
    Product,
    ProductListing,
    ProductSort,
)
from infrastructure.product.models import CategoryModel, CountryModel, ProductModel
from infrastructure.review.models import ReviewModel


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


    async def search(
        self,
        *,
        q: str | None = None,
        country_slug: str | None = None,
        category_slug: str | None = None,
        ids: list[int] | None = None,
        sort: ProductSort = ProductSort.RECOMMEND,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ProductListing], int]:
        """검색 · 필터 · 정렬 · 페이지 (프론트 lib/products.ts findProducts 와 같은 규칙). (목록, 전체 개수)"""
        keyword = _normalize(q) if q else ""
        conditions = []
        if keyword:
            haystack = _normalized(
                func.concat_ws(
                    " ", ProductModel.name, CountryModel.name, CategoryModel.name,
                    ProductModel.manufacturer, ProductModel.food_type, ProductModel.description,
                )
            )
            conditions.append(haystack.like(f"%{_escape_like(keyword)}%", escape="\\"))
        if country_slug == OTHER_COUNTRY_SLUG:
            conditions.append(CountryModel.slug.is_(None))
        elif country_slug:
            conditions.append(CountryModel.slug == country_slug)
        if category_slug:
            conditions.append(CategoryModel.slug == category_slug)
        if ids is not None:
            conditions.append(ProductModel.product_id.in_(ids))

        total = await self.session.scalar(
            select(func.count()).select_from(ProductModel).join(ProductModel.country).join(ProductModel.category).where(*conditions)
        )
        stmt, rating, review_count = _listing_query()
        name_first = case((_normalized(ProductModel.name).like(f"%{_escape_like(keyword)}%", escape="\\"), 0), else_=1)
        sale_price = case(
            (and_(ProductModel.discount_price.is_not(None), ProductModel.discount_price < ProductModel.price), ProductModel.discount_price),
            else_=ProductModel.price,
        )
        order_by = {
            ProductSort.RECOMMEND: [name_first, rating.desc()] if keyword else [rating.desc()],
            ProductSort.REVIEW: [review_count.desc()],
            ProductSort.LOW: [sale_price],
            ProductSort.HIGH: [sale_price.desc()],
            ProductSort.NEW: [ProductModel.is_new.desc(), ProductModel.product_id.desc()],
        }[sort]
        rows = await self.session.execute(
            stmt.where(*conditions)
            # 품절은 늘 맨 뒤, 같은 순위면 id 순 (페이지가 바뀌어도 순서가 흔들리지 않게)
            .order_by(ProductModel.stock == 0, *order_by, ProductModel.product_id)
            .offset((page - 1) * size)
            .limit(size)
        )
        return [_to_listing(*row) for row in rows.all()], total

    async def get_listing(self, product_id: int) -> ProductListing | None:
        """상세 화면용: 상품 + 평점 · 리뷰 수."""
        stmt, _, _ = _listing_query()
        row = (await self.session.execute(stmt.where(ProductModel.product_id == product_id))).first()
        return _to_listing(*row) if row else None

    async def list_categories(self) -> list[CategorySummary]:
        rows = await self.session.execute(
            select(CategoryModel.slug, CategoryModel.name, func.count(ProductModel.product_id))
            .outerjoin(CategoryModel.products)
            .group_by(CategoryModel.category_id)
            .order_by(CategoryModel.category_id)
        )
        return [CategorySummary(slug, name, count) for slug, name, count in rows.all()]


def _listing_query():
    """상품 + 나라 · 카테고리 + 리뷰 집계. (select 문, 평점 컬럼, 리뷰 수 컬럼)"""
    stats = (
        select(
            ReviewModel.product_id,
            func.round(func.avg(ReviewModel.rating), 1).label("rating"),
            func.count().label("review_count"),
        )
        .group_by(ReviewModel.product_id)
        .subquery()
    )
    rating = func.coalesce(stats.c.rating, 0)
    review_count = func.coalesce(stats.c.review_count, 0)
    stmt = (
        select(ProductModel, rating, review_count)
        .join(ProductModel.country)
        .join(ProductModel.category)
        .outerjoin(stats, stats.c.product_id == ProductModel.product_id)
        .options(contains_eager(ProductModel.country), contains_eager(ProductModel.category))
    )
    return stmt, rating, review_count


def _normalize(text: str) -> str:
    """검색어 비교용: 소문자 + 공백 제거 ("도쿄 바나나" = "도쿄바나나")."""
    return re.sub(r"\s+", "", text).lower()


def _normalized(column):
    """_normalize 와 같은 변환을 DB 에서."""
    return func.lower(func.regexp_replace(column, r"\s+", "", "g"))


def _escape_like(text: str) -> str:
    # 검색어의 % _ \ 는 글자 그대로 찾아요
    return text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _to_listing(row: ProductModel, rating, review_count) -> ProductListing:
    return ProductListing(_to_domain(row), float(rating), int(review_count))


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
