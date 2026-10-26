"""상품 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.product.service import ProductService
from database import get_session
from domain.product.product import ProductSort
from presentation.product.schemas import CategoryOut, ProductOut
from presentation.schemas import Page

router = APIRouter(tags=["product"])

CountrySlug = Literal["japan", "taiwan", "china", "vietnam", "other"]


def get_product_service(session: AsyncSession = Depends(get_session)) -> ProductService:
    return ProductService(session)


@router.get("/products", response_model=Page[ProductOut])
async def list_products(
    q: str | None = Query(None, max_length=50, description="검색어 (대소문자 · 띄어쓰기 무시)"),
    country: CountrySlug | None = Query(None, description="other = 일본 · 대만 · 중국 · 베트남이 아닌 나라"),
    category: str | None = Query(None, max_length=30, description="카테고리 slug (GET /categories)"),
    ids: str | None = Query(None, pattern=r"^\d+(,\d+){0,99}$", description="쉼표로 구분한 상품 번호, 최대 100개 (픽 페이지용)"),
    sort: ProductSort = Query(ProductSort.RECOMMEND),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
) -> Page[ProductOut]:
    listings, total = await service.search(
        q=q,
        country_slug=country,
        category_slug=category,
        ids=[int(i) for i in ids.split(",")] if ids else None,
        sort=sort,
        page=page,
        size=size,
    )
    return Page.of([ProductOut.of(listing) for listing in listings], total, page, size)


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int = Path(ge=1), service: ProductService = Depends(get_product_service)
) -> ProductOut:
    return ProductOut.of(await service.get(product_id))


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(service: ProductService = Depends(get_product_service)) -> list[CategoryOut]:
    return [CategoryOut.of(c) for c in await service.categories()]
