from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from infrastructure import models as _models  # noqa: F401  (모든 ORM 모델을 Base.metadata 에 등록)
from presentation.admin.router import router as admin_router
from presentation.auth.router import router as auth_router
from presentation.cart.router import router as cart_router
from presentation.exception_handlers import register_exception_handlers
from presentation.health.router import router as health_router
from presentation.order.router import router as order_router
from presentation.product.router import router as product_router
from presentation.review.router import router as review_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 테이블 생성 (이미 있는 테이블은 건드리지 않음). 시드는 별도 스크립트(SCRUM-15).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Gourmand API", version="0.1.0", lifespan=lifespan)

# TODO(SCRUM-17): CORS·요청 로깅 미들웨어
register_exception_handlers(app)

for r in (health_router, auth_router, product_router, review_router, cart_router, order_router, admin_router):
    app.include_router(r)
