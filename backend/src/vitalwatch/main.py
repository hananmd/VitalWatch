"""FastAPI application factory.

Run locally with: ``uv run uvicorn vitalwatch.main:app --reload``
"""

from typing import Literal

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from vitalwatch import __version__
from vitalwatch.config import Settings
from vitalwatch.core.auth import redact_passwords
from vitalwatch.core.auth import router as auth_router
from vitalwatch.core.passwords import make_hasher
from vitalwatch.db import make_engine


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="VitalWatch Core API", version=__version__)
    app.state.settings = settings
    app.state.password_hasher = make_hasher(settings.environment)
    if settings.database_url is not None:
        app.state.engine = make_engine(settings.database_url.get_secret_value())

    @app.exception_handler(RequestValidationError)
    async def hide_passwords_in_validation_errors(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # FastAPI's default body includes the submitted password under "input".
        detail = redact_passwords(jsonable_encoder(exc.errors()))
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.get("/health", tags=["health"], summary="Liveness check")
    def health() -> HealthResponse:
        return HealthResponse()

    app.include_router(auth_router)
    return app


app = create_app()
