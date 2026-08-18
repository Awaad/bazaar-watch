from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from bazaarwatch.app import create_app
from bazaarwatch.core.settings import Settings


@asynccontextmanager
async def client_for(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Runs the lifespan, so app.state carries the engine and redis client that
    readiness probes. Without it we would be testing an AttributeError."""
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_liveness_does_not_touch_dependencies(settings: Settings) -> None:
    """Liveness must answer while Postgres and Redis are unreachable. If it did
    not, a database blip would restart every API container, turning a
    recoverable dependency failure into an outage."""
    async with client_for(settings) as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_reports_503_when_dependencies_are_down(settings: Settings) -> None:
    async with client_for(settings) as client:
        response = await client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"] == {"postgres": False, "redis": False}


@pytest.mark.asyncio
async def test_health_is_outside_the_version_prefix(settings: Settings) -> None:
    """Health is operational, not part of the client contract, and must not
    move when the contract does."""
    async with client_for(settings) as client:
        assert (await client.get("/v1/health/live")).status_code == 404
