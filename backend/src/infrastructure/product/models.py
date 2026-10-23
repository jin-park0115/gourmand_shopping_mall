"""상품 ORM 모델 (인수 당시 legacy/models.py 에서 이전)."""
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CountryModel(Base):
    __tablename__ = "country"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    products: Mapped[list["ProductModel"]] = relationship(back_populates="country")


class CategoryModel(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

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
