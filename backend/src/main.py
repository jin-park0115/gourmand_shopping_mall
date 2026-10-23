from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from presentation.admin.router import router as admin_router
from presentation.auth.router import router as auth_router
from presentation.cart.router import router as cart_router
from presentation.health.router import router as health_router
from presentation.order.router import router as order_router
from presentation.product.router import router as product_router
from presentation.review.router import router as review_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(SCRUM-14): 시작 시 테이블 생성·시드 확인
    yield
    await engine.dispose()


app = FastAPI(title="Gourmand API", version="0.1.0", lifespan=lifespan)

# TODO(SCRUM-17): CORS·요청 로깅 미들웨어
# TODO(SCRUM-16): 도메인 예외 → HTTP 응답 exception handler

for r in (health_router, auth_router, product_router, review_router, cart_router, order_router, admin_router):
    app.include_router(r)
