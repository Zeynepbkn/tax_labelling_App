"""enforce one labeling record per document (grandfather existing duplicates)

Aynı belgenin farklı kullanıcılarca birden çok kez etiketlenmesini DB seviyesinde
engeller. Halihazırda mükerrer kaydı olan belgeler muaf tutulur (eski veriye
dokunulmaz); diğer tüm belgeler -- yeni etiketlenecek her belge dahil -- için
belge başına en fazla bir etiketleme kaydı kuralı uygulanır.

Muafiyet listesi migration çalışırken dinamik hesaplanır: temiz bir veritabanında
(mükerrer yokken) tam bir unique index oluşur.

Revision ID: e8f2a1c9d740
Revises: c4e1f7a93d22
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e8f2a1c9d740"
down_revision = "c4e1f7a93d22"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_labeling_records_document_single"


def upgrade() -> None:
    conn = op.get_bind()
    duplicate_ids = [
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT document_id FROM labeling_records "
                "GROUP BY document_id HAVING count(*) > 1 ORDER BY document_id"
            )
        )
    ]

    if duplicate_ids:
        id_list = ", ".join(str(int(i)) for i in duplicate_ids)
        where_clause = f"WHERE document_id NOT IN ({id_list})"
    else:
        where_clause = ""

    conn.execute(
        sa.text(
            f"CREATE UNIQUE INDEX {INDEX_NAME} "
            f"ON labeling_records (document_id) {where_clause}"
        )
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="labeling_records")
