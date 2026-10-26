"""SCRUM-59 Neon 연결 주소를 asyncpg 형식으로 바꾸는지 검사합니다."""
import pytest

from core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Neon 대시보드에서 복사한 그대로
        (
            "postgresql://u:p%40w@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p%40w@ep-x.neon.tech/neondb?ssl=require",
        ),
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        # 이미 asyncpg 형식이면 그대로
        ("postgresql+asyncpg://u:p@localhost:5432/gourmand", "postgresql+asyncpg://u:p@localhost:5432/gourmand"),
        ("postgresql+asyncpg://u:p@h/db?ssl=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
    ],
)
def test_database_url_is_normalized_for_asyncpg(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected
