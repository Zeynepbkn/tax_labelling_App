from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import admin, auth, documents, labeling, quiz, training, users
from app.services.admin_service import ensure_initial_admin
from app.services.bootstrap_service import ensure_seed_data


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("taxlabeltr")


def create_app() -> FastAPI:
    settings = get_settings()
    cors_origins = settings.cors_origin_list or ["*"]
    project_root = Path(__file__).resolve().parents[2]
    frontend_dist = project_root / "frontend" / "dist"
    frontend_assets = frontend_dist / "assets"

    app = FastAPI(title="TaxLabelTR Backend", version="0.1.0")

    @app.middleware("http")
    async def log_requests(request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception("request failed method=%s path=%s elapsed_ms=%.1f", request.method, request.url.path, elapsed_ms)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        if request.url.path.startswith("/api"):
            logger.info(
                "request method=%s path=%s status=%s elapsed_ms=%.1f",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response

    # Frontend daha sonra ekleneceği için şimdilik geniş CORS (prod'da daraltılmalı)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials="*" not in cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(training.router, prefix="/api")
    app.include_router(quiz.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(labeling.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=frontend_assets), name="assets")

    if frontend_dist.exists():
        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_frontend(full_path: str):
            index_file = frontend_dist / "index.html"
            return FileResponse(index_file)

    @app.on_event("startup")
    def _startup() -> None:
        logger.info("application startup")
        ensure_initial_admin()
        ensure_seed_data()

    return app


app = create_app()

