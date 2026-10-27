from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# 예시 · 기본값으로 쓰인 적 있는 키. 길이와 상관없이 막아요
WEAK_JWT_SECRETS = {"change-me", "changeme", "secret", "your-secret-key"}
MIN_JWT_SECRET_BYTES = 32


class Settings(BaseSettings):
    """환경변수(.env) 설정. 실제 비밀값은 .env 에만 둡니다."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gourmand"
    cors_origins: str = "http://localhost:3000"

    # 기본값은 일부러 막혀 있어요. .env 나 배포 환경변수에 꼭 따로 넣어 주세요 (아래 _strong_jwt_secret)
    jwt_secret_key: str = Field("change-me", validate_default=True)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # 시드 계정 (SCRUM-15). 비밀번호가 비어 있으면 그 계정은 만들지 않아요
    admin_email: str = "admin@gourmand.com"
    admin_password: str | None = None
    customer_email: str = "customer@gourmand.com"
    customer_password: str | None = None

    @field_validator("database_url")
    @classmethod
    def _asyncpg_url(cls, value: str) -> str:
        """Neon 이 주는 주소(postgresql://...?sslmode=require&channel_binding=require)를
        그대로 붙여 넣어도 asyncpg 로 연결되게 바꿔요. asyncpg 는 sslmode 대신 ssl 을 받아요."""
        url = make_url(value)
        if url.drivername in ("postgresql", "postgres"):
            url = url.set(drivername="postgresql+asyncpg")
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        if sslmode and "ssl" not in query:
            query["ssl"] = sslmode
        return url.set(query=query).render_as_string(hide_password=False)

    @field_validator("jwt_secret_key")
    @classmethod
    def _strong_jwt_secret(cls, value: str) -> str:
        """키를 안 넣고 띄우면 누구나 아는 "change-me" 로 관리자 토큰을 위조할 수 있어서, 아예 시작을 막아요.
        HS256 키는 32바이트 이상을 권해요 (RFC 7518)."""
        if value.strip() in WEAK_JWT_SECRETS or len(value.encode()) < MIN_JWT_SECRET_BYTES:
            raise ValueError(
                f"JWT_SECRET_KEY 를 {MIN_JWT_SECRET_BYTES}바이트 이상의 무작위 값으로 설정해 주세요. "
                'backend/.env 에 넣거나 배포 환경변수로 주면 돼요. 만들기: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        # 브라우저 Origin 에는 끝 "/" 가 없어요. 대시보드에 "https://x.vercel.app/" 로 넣어도 맞게 떼요
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
