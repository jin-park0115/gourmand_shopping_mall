"""DB가 필요한 테스트용 공통 fixture.

실제 개발 DB(gourmand)는 건드리지 않고, 같은 서버의 테스트 DB(기본 `gourmand_test`)를 써요.
테스트마다 트랜잭션 안에서 테이블을 만들고 끝나면 통째로 rollback 해서, 아무것도 남지 않아요.
PostgreSQL 에 접속할 수 없으면(.env 없음 등) DB 테스트는 건너뛰어요.
"""
import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import get_settings
from database import Base
from infrastructure import models as _models  # noqa: F401  (모든 ORM 모델을 Base.metadata 에 등록)


def _test_database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    url = make_url(get_settings().database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


async def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database})
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        await admin.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_login_guard():
    # 로그인 연속 실패 잠금은 서버 메모리라, 테스트끼리 실패 횟수가 이어지지 않게 매번 비워요
    from application.auth.service import login_guard

    login_guard.reset()
    yield
    login_guard.reset()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    url = _test_database_url()
    try:
        await _ensure_database(url)
    except Exception as exc:  # 접속 정보가 없거나 서버가 꺼져 있으면 DB 테스트만 건너뛰어요
        pytest.skip(f"테스트 DB에 접속할 수 없어요: {type(exc).__name__}")

    engine = create_async_engine(url)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        await conn.run_sync(Base.metadata.create_all)
        # 서비스가 commit 해도 바깥 트랜잭션 안의 savepoint 만 확정돼서, 끝에 rollback 하면 다 사라져요
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()
