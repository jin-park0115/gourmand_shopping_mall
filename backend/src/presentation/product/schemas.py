"""상품 요청·응답 Pydantic 스키마."""
from domain.product.product import CategorySummary, ProductListing
from presentation.schemas import CamelModel


class ProductOut(CamelModel):
    """프론트 types/product.ts 의 Product 와 같은 모양 (+ countrySlug · categorySlug)."""

    id: int
    name: str
    price: int
    discount_price: int | None
    country: str
    country_slug: str
    category: str
    category_slug: str
    image_url: str
    description: str
    is_new: bool
    rating: float
    review_count: int
    stock: int
    is_sold_out: bool
    delivery_days: int
    volume: float
    unit: str
    item_count: int
    origin: str
    food_type: str
    manufacturer: str
    storage_method: str

    @classmethod
    def of(cls, listing: ProductListing) -> "ProductOut":
        p = listing.product
        return cls(**vars(p), is_sold_out=p.is_sold_out, rating=listing.rating, review_count=listing.review_count)


class CategoryOut(CamelModel):
    slug: str
    name: str
    product_count: int

    @classmethod
    def of(cls, category: CategorySummary) -> "CategoryOut":
        return cls(**vars(category))


class SuggestProductOut(CamelModel):
    """자동완성 한 줄에 필요한 것만."""

    id: int
    name: str
    image_url: str
    price: int
    sale_price: int
    is_sold_out: bool

    @classmethod
    def of(cls, listing: ProductListing) -> "SuggestProductOut":
        p = listing.product
        return cls(id=p.id, name=p.name, image_url=p.image_url, price=p.price, sale_price=p.sale_price, is_sold_out=p.is_sold_out)


class SuggestCountryOut(CamelModel):
    slug: str
    name: str


class SuggestOut(CamelModel):
    total: int  # 검색 결과 전체 개수 ("전체 결과 N개 보기")
    products: list[SuggestProductOut]
    categories: list[CategoryOut]
    countries: list[SuggestCountryOut]
