from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402


TABLES = [
    "users",
    "documents",
    "training_labels",
    "training_label_questions",
    "quiz_questions",
    "quiz_attempts",
    "labeling_records",
    "labeling_questions",
    "activity_logs",
]


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

    with engine.connect() as connection:
        version = connection.execute(text("select version()")).scalar_one()
        current_db = connection.execute(text("select current_database()")).scalar_one()
        current_user = connection.execute(text("select current_user")).scalar_one()

        print("Database connection OK")
        print(f"Database: {current_db}")
        print(f"User: {current_user}")
        print(f"Version: {version.split(',')[0]}")

        existing = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    select table_name
                    from information_schema.tables
                    where table_schema = 'public'
                    order by table_name
                    """
                )
            )
        }

        print("\nTables:")
        for table in TABLES:
            if table not in existing:
                print(f"  - {table}: MISSING")
                continue
            count = connection.execute(text(f'select count(*) from "{table}"')).scalar_one()
            print(f"  - {table}: {count} rows")

        extra = sorted(existing.difference(TABLES).difference({"alembic_version"}))
        if extra:
            print("\nExtra public tables:")
            for table in extra:
                print(f"  - {table}")


if __name__ == "__main__":
    main()
