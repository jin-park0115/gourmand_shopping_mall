"""시드 실행: `uv run python scripts/seed.py` (backend 폴더에서, `alembic upgrade head` 다음에)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import get_settings  # noqa: E402
from database import SessionLocal, engine  # noqa: E402
from infrastructure.seed import run_seed  # noqa: E402


async def main() -> None:
    async with SessionLocal() as session:
        result = await run_seed(session, get_settings())
    await engine.dispose()
    print(f"나라 {result.countries}개 · 카테고리 {result.categories}개 · 상품 {result.products}개 · 리뷰 {result.reviews}개")
    for email in result.accounts:
        print(f"계정 준비됨: {email}")
    for kind in result.skipped_accounts:
        print(f"{kind} 계정은 건너뜀: .env 에 {kind.upper()}_PASSWORD 를 넣으면 만들어져요")


if __name__ == "__main__":
    asyncio.run(main())
