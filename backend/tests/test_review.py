"""SCRUM-25: 리뷰 도메인 규칙 (순수 파이썬)."""
from datetime import datetime

import pytest

from domain.exceptions import InvalidValueError, PermissionDeniedError
from domain.review.review import Review, validate_content, validate_rating


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_out_of_range(rating) -> None:
    with pytest.raises(InvalidValueError, match="별점"):
        validate_rating(rating)


def test_rating_in_range() -> None:
    assert [validate_rating(r) for r in (1, 5)] == [1, 5]


@pytest.mark.parametrize("content", ["너무 짧아요", "   공백  빼면 짧아   ", "가" * 1001])
def test_content_length(content) -> None:
    with pytest.raises(InvalidValueError, match="10~1000자"):
        validate_content(content)


def test_content_is_trimmed() -> None:
    assert validate_content("  열 글자가 넘는 리뷰예요  ") == "열 글자가 넘는 리뷰예요"


def test_only_owner_can_change() -> None:
    review = Review(1, 3, member_id=7, author_name="김구르", rating=5, content="맛있어요 맛있어요",
                    created_at=datetime(2026, 10, 26), updated_at=None)
    review.check_owner(7, "수정")  # 본인은 통과
    with pytest.raises(PermissionDeniedError, match="본인이 작성한 리뷰만 삭제할 수 있어요"):
        review.check_owner(8, "삭제")
