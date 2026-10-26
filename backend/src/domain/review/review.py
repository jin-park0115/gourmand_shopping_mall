"""리뷰 도메인 객체와 규칙 (순수 파이썬).

규칙: 별점 1~5, 내용은 앞뒤 공백을 뺀 10~1000자, 상품당 1인 1리뷰(Repository · DB UNIQUE 가 막아요),
본인 리뷰만 수정 · 삭제 (관리자도 남의 리뷰는 못 고쳐요).
"""
from dataclasses import dataclass
from datetime import datetime

from domain.exceptions import InvalidValueError, PermissionDeniedError

RATING_MIN, RATING_MAX = 1, 5
CONTENT_MIN_LENGTH, CONTENT_MAX_LENGTH = 10, 1000
DUPLICATE_MESSAGE = "이미 이 상품에 리뷰를 작성했어요."


@dataclass(frozen=True)
class Review:
    id: int
    product_id: int
    member_id: int
    author_name: str  # 회원 이름 (리뷰 테이블이 아니라 member 에서 가져와요)
    rating: int
    content: str
    created_at: datetime
    updated_at: datetime | None

    def check_owner(self, member_id: int, action: str) -> None:
        """action: '수정' · '삭제'. 남의 리뷰면 403."""
        if self.member_id != member_id:
            raise PermissionDeniedError(f"본인이 작성한 리뷰만 {action}할 수 있어요.")


def validate_rating(rating: int) -> int:
    if not RATING_MIN <= rating <= RATING_MAX:
        raise InvalidValueError(f"별점은 {RATING_MIN}~{RATING_MAX}점이어야 해요.")
    return rating


def validate_content(content: str) -> str:
    """앞뒤 공백을 뺀 내용을 돌려줘요."""
    content = content.strip()
    if not CONTENT_MIN_LENGTH <= len(content) <= CONTENT_MAX_LENGTH:
        raise InvalidValueError(f"리뷰는 {CONTENT_MIN_LENGTH}~{CONTENT_MAX_LENGTH}자로 써 주세요.")
    return content
