from __future__ import annotations


def is_non_empty_text(value: str | None) -> bool:
    return bool(value and value.strip())

