"""상품 ORM 모델 (인수 당시 legacy/models.py 에서 이전)."""
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CountryModel(Base):
    __tablename__ = "country"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # 주요 4개국만 slug 가 있어요 (japan · taiwan · china · vietnam). 없으면 API 에서 "other"
    slug: Mapped[str | None] = mapped_column(String(30), unique=True)

    products: Mapped[list["ProductModel"]] = relationship(back_populates="country")


class CategoryModel(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    slug: Mapped[str] = mapped_column(String(30), unique=True)  # 프론트 주소 /category/{slug}

    products: Mapped[list["ProductModel"]] = relationship(back_populates="category")


class ProductModel(Base):
    __tablename__ = "product"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("country.country_id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("category.category_id"))

    name: Mapped[str] = mapped_column(String(200))
    manufacturer: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int]
    discount_price: Mapped[int | None]
    image_url: Mapped[str] = mapped_column(String(500))
    is_new: Mapped[bool] = mapped_column(default=False)

    stock: Mapped[int] = mapped_column(default=0)
    delivery_days: Mapped[int]

    volume: Mapped[float] = mapped_column(Numeric(asdecimal=False))
    unit: Mapped[str] = mapped_column(String(10))
    item_count: Mapped[int] = mapped_column(default=1)
    origin: Mapped[str] = mapped_column(String(200))
    food_type: Mapped[str] = mapped_column(String(100))
    storage_method: Mapped[str] = mapped_column(String(300))

    country: Mapped[CountryModel] = relationship(back_populates="products")
    category: Mapped[CategoryModel] = relationship(back_populates="products")
