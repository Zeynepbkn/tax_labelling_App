from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.document_service import import_annotation_documents, import_training_documents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TaxLabelTR JSON files into the configured database.")
    parser.add_argument("kind", choices=["training", "annotation"])
    parser.add_argument("path")
    args = parser.parse_args()

    json_path = Path(args.path).resolve()
    if not json_path.exists():
        raise SystemExit(f"JSON file not found: {json_path}")

    started = time.perf_counter()
    print(f"Loading {json_path} ...", flush=True)
    with json_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise SystemExit("JSON root must be a list.")

    print(f"Loaded {len(data)} items. Importing {args.kind} data ...", flush=True)
    with SessionLocal() as db:
        if args.kind == "training":
            result = import_training_documents(db, data)
        else:
            result = import_annotation_documents(db, data)

    elapsed = time.perf_counter() - started
    print("Import finished.", flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    print(f"Elapsed seconds: {elapsed:.1f}", flush=True)


if __name__ == "__main__":
    main()
