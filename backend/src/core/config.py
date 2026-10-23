from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수(.env) 설정. 실제 비밀값은 .env 에만 둡니다."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gourmand"
    cors_origins: str = "http://localhost:3000"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # 시드 계정 (SCRUM-15). 비밀번호가 비어 있으면 그 계정은 만들지 않아요
    admin_email: str = "admin@gourmand.local"
    admin_password: str | None = None
    customer_email: str = "customer@gourmand.local"
    customer_password: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
