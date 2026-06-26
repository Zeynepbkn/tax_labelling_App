from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

    with engine.connect() as conn:
        # How many documents have more than one labeling record (across users)?
        dup_docs = conn.execute(
            text(
                """
                select count(*) from (
                    select document_id
                    from labeling_records
                    group by document_id
                    having count(*) > 1
                ) t
                """
            )
        ).scalar_one()

        total_records = conn.execute(text("select count(*) from labeling_records")).scalar_one()
        distinct_docs = conn.execute(
            text("select count(distinct document_id) from labeling_records")
        ).scalar_one()

        print(f"Toplam labeling kaydi      : {total_records}")
        print(f"Etiketlenmis farkli belge  : {distinct_docs}")
        print(f"Birden fazla etiketlenen   : {dup_docs} belge")
        print(f"Fazla (silinebilecek) kayit: {total_records - distinct_docs}")
        print()

        rows = conn.execute(
            text(
                """
                select
                    lr.document_id,
                    d.evrak_id,
                    count(*) as n,
                    array_agg(lr.user_id order by lr.created_at) as users,
                    array_agg(lr.id order by lr.created_at) as record_ids,
                    array_agg(lr.created_at order by lr.created_at) as created_ats
                from labeling_records lr
                join documents d on d.id = lr.document_id
                group by lr.document_id, d.evrak_id
                having count(*) > 1
                order by n desc, lr.document_id
                """
            )
        ).all()

        print(f"=== Cogul etiketlenen {len(rows)} belge ===")
        for r in rows:
            print(f"\ndoc_id={r.document_id} evrak_id={r.evrak_id} kez={r.n}")
            for uid, rid, ts in zip(r.users, r.record_ids, r.created_ats):
                print(f"    user={uid:>4}  record_id={rid:>5}  created_at={ts}")


if __name__ == "__main__":
    main()
