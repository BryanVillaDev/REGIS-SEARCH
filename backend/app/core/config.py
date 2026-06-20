from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_timezone: str = "America/Bogota"
    jwt_secret: str = Field(default="change-me", min_length=8)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 8 * 60

    # API key para integraciones maquina-a-maquina (endpoints sin JWT).
    api_key: str | None = Field(default=None, alias="REGIS_API_KEY")

    clickhouse_url: str = "http://localhost:8123"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "app"
    clickhouse_secure: bool = False

    cors_origins_raw: str = Field(default="http://localhost:5173,http://localhost:3000", alias="CORS_ORIGINS")
    query_timeout_seconds: int = 30
    bulk_chunk_size: int = 5000
    worker_poll_seconds: int = 3
    export_dir: str = "/exports"
    xlsx_max_rows: int = 200000

    bootstrap_admin_user: str | None = Field(default=None, alias="REGIS_BOOTSTRAP_ADMIN_USER")
    bootstrap_admin_password: str | None = Field(default=None, alias="REGIS_BOOTSTRAP_ADMIN_PASSWORD")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
