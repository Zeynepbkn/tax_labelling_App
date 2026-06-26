from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, Computed, UniqueConstraint
from sqlalchemy.orm import RelationshipProperty


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.base import Base  # noqa: E402
from app.db import models  # noqa: F401, E402


def main() -> None:
    print("TaxLabelTR database schema")
    print("=" * 28)

    for table_name in sorted(Base.metadata.tables):
        table = Base.metadata.tables[table_name]
        print(f"\nTABLE {table.name}")
        print("-" * (6 + len(table.name)))

        print("Columns:")
        for column in table.columns:
            nullable = "nullable" if column.nullable else "not null"
            default = ""
            if isinstance(column.server_default, Computed):
                default = f", computed={column.server_default.sqltext}"
            elif column.server_default is not None:
                default = f", server_default={column.server_default.arg}"
            elif column.default is not None:
                default = f", default={column.default.arg}"
            print(f"  - {column.name}: {column.type} ({nullable}{default})")

        if table.primary_key.columns:
            pk_cols = ", ".join(col.name for col in table.primary_key.columns)
            print(f"Primary key: {pk_cols}")

        if table.foreign_keys:
            print("Foreign keys:")
            for fk in sorted(table.foreign_keys, key=lambda item: item.parent.name):
                ondelete = f", ondelete={fk.ondelete}" if fk.ondelete else ""
                print(f"  - {fk.parent.name} -> {fk.column.table.name}.{fk.column.name}{ondelete}")

        indexes = sorted(table.indexes, key=lambda idx: idx.name or "")
        if indexes:
            print("Indexes:")
            for index in indexes:
                cols = ", ".join(col.name for col in index.columns)
                unique = " unique" if index.unique else ""
                print(f"  - {index.name}: ({cols}){unique}")

        constraints = [
            constraint
            for constraint in table.constraints
            if constraint.__class__.__name__ not in {"PrimaryKeyConstraint", "ForeignKeyConstraint"}
        ]
        if constraints:
            print("Constraints:")
            for constraint in sorted(constraints, key=lambda item: item.name or ""):
                if isinstance(constraint, CheckConstraint):
                    print(f"  - {constraint.name}: CHECK ({constraint.sqltext})")
                elif isinstance(constraint, UniqueConstraint):
                    cols = ", ".join(col.name for col in constraint.columns)
                    print(f"  - {constraint.name}: UNIQUE ({cols})")
                else:
                    print(f"  - {constraint.name}: {constraint}")

    print("\nORM relationships")
    print("-" * 17)
    for mapper in sorted(Base.registry.mappers, key=lambda item: item.class_.__name__):
        relationships = [
            prop
            for prop in mapper.attrs
            if isinstance(prop, RelationshipProperty)
        ]
        if not relationships:
            continue
        print(f"\n{mapper.class_.__name__}:")
        for rel in sorted(relationships, key=lambda item: item.key):
            many = "many" if rel.uselist else "one"
            print(f"  - {rel.key}: {many} {rel.mapper.class_.__name__}")


if __name__ == "__main__":
    main()
