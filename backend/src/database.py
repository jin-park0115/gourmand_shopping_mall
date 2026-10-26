"""공통 비동기 DB 설정 (SQLAlchemy 2.x + asyncpg).

스키마 변경은 Alembic 마이그레이션(migrations/)으로 관리합니다.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """요청마다 세션을 열고 닫습니다. commit/rollback 은 응용 서비스가 담당합니다."""
    async with SessionLocal() as session:
        yield session
