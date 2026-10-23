"""공통 비동기 DB 설정 (SQLAlchemy 2.x + asyncpg).

TODO(SCRUM-14): lifespan 테이블 생성·시드 연결, /health/db 검증 보완
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
