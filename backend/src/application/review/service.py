"""리뷰 응용 서비스: Repository 조회 → 도메인 메서드 실행 → 저장 → commit/rollback."""
from sqlalchemy.ext.asyncio import AsyncSession

from domain.exceptions import NotFoundError
from domain.review.review import Review, validate_content, validate_rating
from infrastructure.product.repositories import ProductRepository
from infrastructure.review.repositories import ReviewRepository


class ReviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.reviews = ReviewRepository(session)
        self.products = ProductRepository(session)

    async def list(self, product_id: int, *, page: int, size: int) -> tuple[list[Review], int]:
        await self._ensure_product(product_id)
        return await self.reviews.list_by_product(product_id, page=page, size=size)

    async def create(self, product_id: int, member_id: int, *, rating: int, content: str) -> Review:
        await self._ensure_product(product_id)
        review = await self.reviews.add(
            product_id=product_id, member_id=member_id, rating=validate_rating(rating), content=validate_content(content)
        )
        await self.session.commit()
        return review

    async def update(self, review_id: int, member_id: int, *, rating: int | None, content: str | None) -> Review:
        """보낸 값만 바꿔요."""
        review = await self._review(review_id)
        review.check_owner(member_id, "수정")
        updated = await self.reviews.update(
            review_id,
            rating=review.rating if rating is None else validate_rating(rating),
            content=review.content if content is None else validate_content(content),
        )
        await self.session.commit()
        return updated

    async def delete(self, review_id: int, member_id: int) -> None:
        review = await self._review(review_id)
        review.check_owner(member_id, "삭제")
        await self.reviews.delete(review_id)
        await self.session.commit()

    async def _ensure_product(self, product_id: int) -> None:
        if await self.products.get(product_id) is None:
            raise NotFoundError("상품을 찾을 수 없어요.")

    async def _review(self, review_id: int) -> Review:
        review = await self.reviews.get(review_id)
        if review is None:
            raise NotFoundError("리뷰를 찾을 수 없어요.")
        return review
