"""Health endpoints.

Liveness and readiness are deliberately separate. Liveness answers "is this
process alive", and a failing liveness check should restart the container.
Readiness answers "can this process serve traffic", which depends on Postgres
and Redis, and a failing readiness check should remove the instance from
rotation without restarting it.

Collapsing them means a database blip restarts every API container, which turns
a recoverable dependency failure into an outage.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(tags=["health"])

_PROBE_TIMEOUT_SECONDS = 2.0


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class DependencyStatus(BaseModel):
    postgres: bool
    redis: bool


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: DependencyStatus


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """No dependency checks. If this does not answer, the process is gone."""
    return LivenessResponse(status="ok")


async def _postgres_ok(engine: AsyncEngine) -> bool:
    try:
        async with asyncio.timeout(_PROBE_TIMEOUT_SECONDS):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _redis_ok(redis: Redis) -> bool:
    try:
        async with asyncio.timeout(_PROBE_TIMEOUT_SECONDS):
            await redis.ping()
        return True
    except Exception:
        return False


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    engine: AsyncEngine = request.app.state.engine
    redis: Redis = request.app.state.redis

    postgres, redis_alive = await asyncio.gather(_postgres_ok(engine), _redis_ok(redis))
    ready = postgres and redis_alive

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if ready else "degraded",
        dependencies=DependencyStatus(postgres=postgres, redis=redis_alive),
    )
