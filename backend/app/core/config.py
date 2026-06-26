from __future__ import annotations

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """
    Ortam değişkenleri bu adımda yalnızca taslak olarak modellenir.
    Uygulama runtime'da `DATABASE_URL` üzerinden PostgreSQL'e bağlanacaktır.
    """

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_exp_minutes: int = Field(default=60 * 24, validation_alias="ACCESS_TOKEN_EXP_MINUTES")


settings = Settings()  # env var'lar pydantic tarafından okunur

