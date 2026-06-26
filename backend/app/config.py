from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(ENV_FILE, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # DB
    database_url: str = Field(validation_alias="DATABASE_URL")

    # JWT
    secret_key: str = Field(validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 24, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = "HS256"

    # Bootstrap admin
    admin_username: str | None = Field(default=None, validation_alias="ADMIN_USERNAME")
    admin_email: str | None = Field(default=None, validation_alias="ADMIN_EMAIL")
    admin_password: str | None = Field(default=None, validation_alias="ADMIN_PASSWORD")

    # CORS
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")

    # Uploads
    json_upload_max_mb: int = Field(default=350, validation_alias="JSON_UPLOAD_MAX_MB")

    # Quiz
    quiz_passing_score: int = Field(default=75, validation_alias="QUIZ_PASSING_SCORE")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def json_upload_max_bytes(self) -> int:
        return self.json_upload_max_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

