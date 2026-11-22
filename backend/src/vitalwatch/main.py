"""FastAPI application factory.

Run locally with: ``uv run uvicorn vitalwatch.main:app --reload``
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from vitalwatch import __version__
from vitalwatch.config import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=f"{settings.app_name} Core API",
        version=__version__,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    @app.get("/health", tags=["health"], summary="Liveness check")
    def health() -> HealthResponse:
        return HealthResponse()

    return app


app = create_app()
