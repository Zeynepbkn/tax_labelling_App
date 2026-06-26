from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings


def _get_database_url() -> str:
    # Hugging Face Spaces gibi ortamlarda secret/env üzerinden gelir
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL tanımlı değil.")
    return url


engine = create_engine(
    _get_database_url(),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

