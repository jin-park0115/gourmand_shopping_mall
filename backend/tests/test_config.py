"""SCRUM-59 Neon 연결 주소를 asyncpg 형식으로 바꾸는지, 약한 JWT 키를 막는지 검사합니다."""
import pytest
from pydantic import ValidationError

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


def test_cors_origins_ignore_spaces_and_trailing_slash() -> None:
    settings = Settings(cors_origins=" https://gourmand.vercel.app/ , http://localhost:3000,")
    assert settings.cors_origin_list == ["https://gourmand.vercel.app", "http://localhost:3000"]


@pytest.mark.parametrize("weak", ["change-me", "secret", "short-key", "x" * 31])
def test_weak_jwt_secret_is_rejected(weak: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, jwt_secret_key=weak)


def test_missing_jwt_secret_falls_back_to_default_and_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # 환경변수도 .env 도 없이 띄우면 기본값 change-me 가 들어가는데, 그대로 시작하면 안 돼요
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_long_random_jwt_secret_is_accepted() -> None:
    key = "a" * 32
    assert Settings(_env_file=None, jwt_secret_key=key).jwt_secret_key == key
