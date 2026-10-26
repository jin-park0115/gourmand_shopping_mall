from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """환경변수(.env) 설정. 실제 비밀값은 .env 에만 둡니다."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gourmand"
    cors_origins: str = "http://localhost:3000"

    jwt_secret_key: str = "change-me"
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
