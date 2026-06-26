from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.db.models.labeling import LabelingRecord
from app.db.models.user import User, UserRole
from app.services.document_service import sync_admin_label_to_training
from app.services.labelled_questions_file_service import upsert_labelled_questions_entry


@dataclass
class SyncResult:
    user_id: int
    email: str
    promoted: bool
    synced_records: int


def promote_and_sync(user_id: int, expected_email: str | None = None, dry_run: bool = False) -> SyncResult:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            raise RuntimeError(f"User not found: id={user_id}")

        if expected_email and user.email.lower() != expected_email.lower():
            raise RuntimeError(
                f"Email mismatch for user id={user_id}: database has {user.email!r}, expected {expected_email!r}"
            )

        promoted = user.role != UserRole.admin
        if promoted:
            user.role = UserRole.admin

        stmt = (
            select(LabelingRecord)
            .where(LabelingRecord.user_id == user_id)
            .options(joinedload(LabelingRecord.document), joinedload(LabelingRecord.questions))
            .order_by(LabelingRecord.created_at.asc(), LabelingRecord.id.asc())
        )
        records = db.execute(stmt).scalars().unique().all()

        if dry_run:
            db.rollback()
            return SyncResult(user_id=user.id, email=user.email, promoted=promoted, synced_records=len(records))

        db.commit()

        synced = 0
        for record in records:
            if not record.document:
                continue
            questions = [q.question_text for q in sorted(record.questions, key=lambda item: item.question_order)]
            if not questions:
                continue
            upsert_labelled_questions_entry(record.document, questions)
            sync_admin_label_to_training(db, record.document, questions)
            synced += 1

        return SyncResult(user_id=user.id, email=user.email, promoted=promoted, synced_records=synced)


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a user to admin and sync their labels to labelled_questions.json.")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--email", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = promote_and_sync(user_id=args.user_id, expected_email=args.email, dry_run=args.dry_run)
    action = "would promote" if args.dry_run and result.promoted else "promoted" if result.promoted else "already admin"
    sync_text = "would sync" if args.dry_run else "synced"
    print(
        f"user_id={result.user_id} email={result.email} status={action}; "
        f"{sync_text} {result.synced_records} labeling records"
    )


if __name__ == "__main__":
    main()
