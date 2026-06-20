"""FastAPI application: /api/v1 + (in prod) the built SvelteKit SPA.

In development the SPA runs on the Vite dev server (CORS allows it). In the
Docker image the SPA is built to static files and served here, so the whole app
is one origin / one container.
"""
from __future__ import annotations
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings, ROOT
from .db import init_db
from .api.v1 import api_router

# Built SPA location (override with STATIC_DIR in the container).
STATIC_DIR = Path(os.environ.get("STATIC_DIR", ROOT / "frontend" / "build"))


def create_app() -> FastAPI:
    app = FastAPI(title="Stellegent API", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "ocr_backend": settings.ocr_backend}

    app.include_router(api_router)

    # Serve the built SPA if present (production / Docker).
    if STATIC_DIR.exists():
        app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")
        index = STATIC_DIR / "index.html"

        @app.get("/")
        def _root() -> FileResponse:
            return FileResponse(str(index))

        # SPA client-side routing: any unmatched non-API path -> index.html
        @app.get("/{path:path}")
        def _spa(path: str) -> FileResponse:
            candidate = STATIC_DIR / path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(index))

    return app


app = create_app()
