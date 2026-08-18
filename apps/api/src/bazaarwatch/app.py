"""Application factory.

A factory rather than a module-level app, so tests construct an instance with
their own settings instead of importing a process-wide singleton.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI

from bazaarwatch.core.db import create_engine, create_session_factory
from bazaarwatch.core.errors import ProblemError, problem_error_handler
from bazaarwatch.core.logging import configure_logging
from bazaarwatch.core.redis import create_redis
from bazaarwatch.core.settings import Settings, get_settings
from bazaarwatch.health import router as health_router

API_PREFIX = "/v1"

logger = structlog.get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings

    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.redis = create_redis(settings)

    logger.info("api.startup", environment=settings.environment.value)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
        logger.info("api.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(json_output=settings.is_production)

    app = FastAPI(
        title="Bazaar Watch API",
        version="0.0.0",
        lifespan=lifespan,
        # The specification is emitted from this application and committed;
        # it is never authored by hand. See ADR-0042.
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None if settings.is_production else f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.settings = settings

    app.add_exception_handler(ProblemError, problem_error_handler)

    # Health sits outside the version prefix. It is an operational endpoint, not
    # part of the client contract, and must not move when the contract does.
    app.include_router(health_router)

    return app
