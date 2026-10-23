"""장바구니·찜 ORM 모델."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from infrastructure.product.models import ProductModel


class CartItemModel(Base):
    __tablename__ = "cart_item"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_cart_item_quantity"),)

    member_id: Mapped[int] = mapped_column(ForeignKey("member.member_id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(default=1, server_default="1")
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())

    product: Mapped[ProductModel] = relationship()


class WishlistModel(Base):
    __tablename__ = "wishlist"

    member_id: Mapped[int] = mapped_column(ForeignKey("member.member_id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
