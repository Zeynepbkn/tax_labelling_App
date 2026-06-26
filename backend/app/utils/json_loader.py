from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, UploadFile, status


async def load_json_from_upload(file: UploadFile) -> Any:
    content = await read_upload_bytes(file)
    return parse_json_bytes(content)


async def read_upload_bytes(file: UploadFile, max_size_bytes: int | None = None) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if max_size_bytes is not None and total > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"JSON dosyası çok büyük. Maksimum {max_size_bytes // (1024 * 1024)} MB yüklenebilir.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def parse_json_bytes(content: bytes) -> Any:
    try:
        return json.loads(content.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(content.decode("utf-8-sig"))

