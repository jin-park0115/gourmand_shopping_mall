"""리뷰 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.review.service import ReviewService
from database import get_session
from domain.auth.member import CurrentUser
from presentation.auth.dependencies import get_current_user, get_optional_user
from presentation.review.schemas import ReviewCreateIn, ReviewOut, ReviewUpdateIn, ReviewWritableOut
from presentation.schemas import Page

router = APIRouter(tags=["review"])


def get_review_service(session: AsyncSession = Depends(get_session)) -> ReviewService:
    return ReviewService(session)


@router.get("/products/{product_id}/reviews", response_model=Page[ReviewOut])
async def list_reviews(
    product_id: int = Path(ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: CurrentUser | None = Depends(get_optional_user),  # 공개. 로그인했으면 isMine 계산
    service: ReviewService = Depends(get_review_service),
) -> Page[ReviewOut]:
    reviews, total = await service.list(product_id, page=page, size=size)
    viewer = user.member_id if user else None
    return Page.of([ReviewOut.of(r, viewer) for r in reviews], total, page, size)


@router.get("/products/{product_id}/reviews/writable", response_model=ReviewWritableOut)
async def review_writable(
    product_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewWritableOut:
    message = await service.writable_message(product_id, user.member_id)
    return ReviewWritableOut(can_write=message is None, message=message)


@router.post("/products/{product_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreateIn,
    product_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    review = await service.create(product_id, user.member_id, rating=body.rating, content=body.content)
    return ReviewOut.of(review, user.member_id)


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review(
    body: ReviewUpdateIn,
    review_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    review = await service.update(review_id, user.member_id, rating=body.rating, content=body.content)
    return ReviewOut.of(review, user.member_id)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> Response:
    await service.delete(review_id, user.member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
