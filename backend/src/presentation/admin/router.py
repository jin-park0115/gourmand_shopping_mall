"""관리자 주문 운영 API 라우터 (표현 계층): 요청 검증 → 응용 서비스 호출 → 응답 변환."""
from datetime import date

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.admin.service import AdminOrderQueryService, AdminOrderStatusService
from database import get_session
from domain.admin.views import AdminOrderQuery
from domain.order.status import OrderStatus
from presentation.admin.schemas import (
    AdminOrderOut,
    OrderSummaryOut,
    StatusChangeIn,
    admin_order_page,
)
from presentation.auth.dependencies import CurrentUser, require_admin
from presentation.schemas import Page

# 모든 엔드포인트가 관리자 전용이에요 (토큰 없음 · 로그아웃 401, 고객 403)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def get_query_service(session: AsyncSession = Depends(get_session)) -> AdminOrderQueryService:
    return AdminOrderQueryService(session)


def get_status_service(session: AsyncSession = Depends(get_session)) -> AdminOrderStatusService:
    return AdminOrderStatusService(session)


@router.get("/orders", response_model=Page[AdminOrderOut])
async def list_orders(
    status: OrderStatus | None = Query(None, description="6개 주문 상태 중 하나"),
    q: str | None = Query(None, max_length=50, description="주문번호 · 받는 사람 · 연락처 · 상품명"),
    date_from: date | None = Query(None, alias="from", description="주문일 시작 YYYY-MM-DD (KST)"),
    date_to: date | None = Query(None, alias="to", description="주문일 끝 YYYY-MM-DD (그날 포함)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: AdminOrderQueryService = Depends(get_query_service),
) -> Page[AdminOrderOut]:
    query = AdminOrderQuery(status=status, q=q, date_from=date_from, date_to=date_to, page=page, size=size)
    return admin_order_page(await service.list_orders(query))


# /orders/{order_id} 보다 먼저 둬야 "summary" 가 주문 번호로 잡히지 않아요
@router.get("/orders/summary", response_model=OrderSummaryOut)
async def order_summary(
    q: str | None = Query(None, max_length=50),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    service: AdminOrderQueryService = Depends(get_query_service),
) -> OrderSummaryOut:
    query = AdminOrderQuery(q=q, date_from=date_from, date_to=date_to)
    return OrderSummaryOut.from_summary(await service.summary(query))


@router.get("/orders/{order_id}", response_model=AdminOrderOut)
async def get_order(
    order_id: int = Path(ge=1), service: AdminOrderQueryService = Depends(get_query_service)
) -> AdminOrderOut:
    return AdminOrderOut.from_view(await service.get_order(order_id))


@router.patch("/orders/{order_id}/status", response_model=AdminOrderOut)
async def change_order_status(
    body: StatusChangeIn,
    order_id: int = Path(ge=1),
    admin: CurrentUser = Depends(require_admin),
    service: AdminOrderStatusService = Depends(get_status_service),
) -> AdminOrderOut:
    view = await service.change_status(
        order_id,
        body.status,
        admin_id=admin.member_id,
        courier=body.courier,
        tracking_no=body.tracking_no,
        note=body.note,
    )
    return AdminOrderOut.from_view(view)
