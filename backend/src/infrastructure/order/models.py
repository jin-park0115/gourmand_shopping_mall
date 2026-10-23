"""주문·주문 상품·결제 ORM 모델."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from infrastructure.product.models import ProductModel


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_price >= 0", name="ck_orders_total_price"),
        Index("ix_orders_status_ordered_at", "status", "ordered_at"),  # 관리자 목록 상태 · 기간 필터 (SCRUM-34)
    )

    order_id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("member.member_id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="접수", server_default="접수")
    total_price: Mapped[int]
    recipient: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    zipcode: Mapped[str] = mapped_column(String(10))
    address1: Mapped[str] = mapped_column(String(200))
    address2: Mapped[str | None] = mapped_column(String(200))
    ordered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # 관리자 주문 운영(C, SCRUM-35)이 채우는 값 — 윤강 님 확인 필요 (ERD 'C 제안')
    courier: Mapped[str | None] = mapped_column(String(20))  # 배송중부터 필수
    tracking_no: Mapped[str | None] = mapped_column(String(30))
    admin_note: Mapped[str | None] = mapped_column(String(300))  # 지연 · 취소 사유
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped["PaymentModel | None"] = relationship(
        back_populates="order", cascade="all, delete-orphan", uselist=False
    )


class OrderItemModel(Base):
    __tablename__ = "order_item"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price"),
    )

    order_item_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id"), index=True)
    quantity: Mapped[int]
    unit_price: Mapped[int]  # 주문 당시 가격

    order: Mapped[OrderModel] = relationship(back_populates="items")
    product: Mapped[ProductModel] = relationship()


class PaymentModel(Base):
    __tablename__ = "payment"

    payment_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), unique=True)
    method: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    paid_at: Mapped[datetime | None]

    order: Mapped[OrderModel] = relationship(back_populates="payment")
