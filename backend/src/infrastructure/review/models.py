"""리뷰 ORM 모델 (인수 당시 legacy/models.py 에서 이전, SCRUM-25 에서 회원 연결)."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ReviewModel(Base):
    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        # 상품당 1인 1리뷰. 동시에 두 번 써도 DB 가 막아요 (product_id 가 앞이라 상품별 목록 조회 인덱스도 겸해요)
        UniqueConstraint("product_id", "member_id", name="uq_review_product_member"),
    )

    review_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.product_id", ondelete="CASCADE"))
    member_id: Mapped[int] = mapped_column(ForeignKey("member.member_id", ondelete="CASCADE"))
    rating: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None]  # 수정한 적 없으면 NULL
