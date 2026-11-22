"""FastAPI application factory.

Run locally with: ``uv run uvicorn vitalwatch.main:app --reload``
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from vitalwatch import __version__
from vitalwatch.config import Settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="VitalWatch Core API", version=__version__)
    app.state.settings = settings or Settings()

    @app.get("/health", tags=["health"], summary="Liveness check")
    def health() -> HealthResponse:
        return HealthResponse()

    return app


app = create_app()
