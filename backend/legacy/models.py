from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Country(Base):
    __tablename__ = "country"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="country")


class Category(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
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

    country: Mapped[Country] = relationship(back_populates="products")
    category: Mapped[Category] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),)

    review_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id", ondelete="CASCADE"))
    author_name: Mapped[str] = mapped_column(String(50))
    rating: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="reviews")