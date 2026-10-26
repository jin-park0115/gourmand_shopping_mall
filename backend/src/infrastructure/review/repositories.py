"""리뷰 Repository: ORM 모델 ↔ 도메인 객체 변환, 비동기 조회·저장."""
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import ConflictError
from domain.review.review import DUPLICATE_MESSAGE, Review
from infrastructure.auth.models import MemberModel
from infrastructure.review.models import ReviewModel


class ReviewRepository:
    """commit 은 응용 서비스가 해요."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_product(self, product_id: int, *, page: int, size: int) -> tuple[list[Review], int]:
        """최신순 (같은 시각이면 나중에 쓴 것 먼저). (목록, 전체 개수)"""
        total = await self.session.scalar(
            select(func.count()).select_from(ReviewModel).where(ReviewModel.product_id == product_id)
        )
        rows = await self.session.execute(
            _select_reviews()
            .where(ReviewModel.product_id == product_id)
            .order_by(ReviewModel.created_at.desc(), ReviewModel.review_id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return [_to_domain(*row) for row in rows.all()], total

    async def get(self, review_id: int) -> Review | None:
        row = (await self.session.execute(_select_reviews().where(ReviewModel.review_id == review_id))).first()
        return _to_domain(*row) if row else None

    async def add(self, *, product_id: int, member_id: int, rating: int, content: str) -> Review:
        """같은 회원이 같은 상품에 이미 썼으면 409."""
        if await self.session.scalar(
            select(ReviewModel.review_id).where(ReviewModel.product_id == product_id, ReviewModel.member_id == member_id)
        ):
            raise ConflictError(DUPLICATE_MESSAGE)
        row = ReviewModel(product_id=product_id, member_id=member_id, rating=rating, content=content)
        try:
            async with self.session.begin_nested():  # 동시에 두 번 써서 UNIQUE 에 걸려도 바깥 트랜잭션은 살려요
                self.session.add(row)
        except IntegrityError:
            raise ConflictError(DUPLICATE_MESSAGE) from None
        return await self.get(row.review_id)

    async def update(self, review_id: int, *, rating: int, content: str) -> Review:
        row = await self.session.get(ReviewModel, review_id)
        row.rating, row.content, row.updated_at = rating, content, func.now()
        await self.session.flush()
        await self.session.refresh(row)
        return await self.get(review_id)

    async def delete(self, review_id: int) -> None:
        await self.session.execute(delete(ReviewModel).where(ReviewModel.review_id == review_id))


def _select_reviews():
    return select(ReviewModel, MemberModel.name).join(MemberModel, MemberModel.member_id == ReviewModel.member_id)


def _to_domain(row: ReviewModel, author_name: str) -> Review:
    return Review(
        id=row.review_id,
        product_id=row.product_id,
        member_id=row.member_id,
        author_name=author_name,
        rating=row.rating,
        content=row.content,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
