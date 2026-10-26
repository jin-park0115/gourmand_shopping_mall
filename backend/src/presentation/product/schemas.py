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
