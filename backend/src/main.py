from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.logging import setup_logging
from database import engine
from presentation.admin.router import router as admin_router
from presentation.auth.router import router as auth_router
from presentation.cart.router import router as cart_router
from presentation.exception_handlers import register_exception_handlers
from presentation.health.router import router as health_router
from presentation.middleware import register_middlewares
from presentation.order.router import router as order_router
from presentation.product.router import router as product_router
from presentation.review.router import router as review_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 스키마는 Alembic 으로 관리: `uv run alembic upgrade head`. 시드는 별도 스크립트(SCRUM-15).
    yield
    await engine.dispose()


setup_logging()

app = FastAPI(title="Gourmand API", version="0.1.0", lifespan=lifespan)

register_middlewares(app)
register_exception_handlers(app)

for r in (health_router, auth_router, product_router, review_router, cart_router, order_router, admin_router):
    app.include_router(r)
