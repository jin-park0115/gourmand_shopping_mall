"""리뷰 요청·응답 Pydantic 스키마."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import Field, StringConstraints, field_serializer, model_validator

from domain.review.review import CONTENT_MAX_LENGTH, CONTENT_MIN_LENGTH, RATING_MAX, RATING_MIN, Review
from presentation.schemas import CamelModel

KST = timezone(timedelta(hours=9))

Rating = Annotated[int, Field(ge=RATING_MIN, le=RATING_MAX)]
Content = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=CONTENT_MIN_LENGTH, max_length=CONTENT_MAX_LENGTH)
]


class ReviewCreateIn(CamelModel):
    rating: Rating
    content: Content


class ReviewUpdateIn(CamelModel):
    """보낸 값만 바꿔요. 둘 다 없으면 422."""

    rating: Rating | None = None
    content: Content | None = None

    @model_validator(mode="after")
    def _something_to_change(self):
        if self.rating is None and self.content is None:
            raise ValueError("바꿀 별점이나 내용을 보내 주세요.")
        return self


class ReviewOut(CamelModel):
    id: int
    product_id: int
    author_name: str
    rating: int
    content: str
    created_at: datetime
    updated_at: datetime | None
    is_mine: bool  # 로그인한 요청이고 작성자가 본인이면 true

    @field_serializer("created_at", "updated_at")
    def _kst(self, value: datetime | None) -> str | None:
        # DB 는 시간대 없이 KST 로 저장해요 (관리자 주문 API 와 같은 방식)
        return None if value is None else (value if value.tzinfo else value.replace(tzinfo=KST)).isoformat()

    @classmethod
    def of(cls, review: Review, viewer_id: int | None) -> "ReviewOut":
        return cls(
            id=review.id,
            product_id=review.product_id,
            author_name=review.author_name,
            rating=review.rating,
            content=review.content,
            created_at=review.created_at,
            updated_at=review.updated_at,
            is_mine=viewer_id is not None and review.member_id == viewer_id,
        )
