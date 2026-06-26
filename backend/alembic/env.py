from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

# alembic.exe ile çalışırken sys.path'te backend kökü olmayabiliyor; `import app` için ekle
_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import dotenv_values, load_dotenv
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base

# Modellerin import edilmesi, metadata'ya tablo kayıtlarını ekler
from app.db import models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
env_file = _backend_root / ".env"
load_dotenv(env_file, override=True)


def get_url() -> str:
    # Alembic çalışırken öncelik: env var / secret
    url = os.getenv("DATABASE_URL") or dotenv_values(env_file).get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL tanımlı değil (alembic).")
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
