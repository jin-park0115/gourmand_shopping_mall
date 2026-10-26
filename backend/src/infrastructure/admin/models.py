"""관리자 주문 운영 ORM 모델."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from domain.order.status import OrderStatus

_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in OrderStatus)


class OrderStatusHistoryModel(Base):
    """주문 상태가 바뀔 때마다 한 줄씩 쌓이는 이력 (관리자 화면 이력 표시 · 감사 기록용)."""

    __tablename__ = "order_status_history"
    __table_args__ = (
        CheckConstraint(f"to_status IN ({_STATUS_VALUES})", name="ck_order_status_history_to_status"),
        CheckConstraint(
            f"from_status IS NULL OR from_status IN ({_STATUS_VALUES})", name="ck_order_status_history_from_status"
        ),
        Index("ix_order_status_history_order_changed", "order_id", "changed_at"),
    )

    history_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    from_status: Mapped[str | None] = mapped_column(String(20))  # 첫 접수는 NULL
    to_status: Mapped[str] = mapped_column(String(20))
    # 바꾼 관리자. 고객 취소 · 주문 생성은 NULL, 회원이 지워져도 이력은 남겨요
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("member.member_id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(300))
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())
