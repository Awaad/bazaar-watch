"""Redis client.

Cache, rate limiting, locks and the job queue. The domain event bus is
deferred; see ADR-0005.
"""

from __future__ import annotations

from redis.asyncio import Redis

from bazaarwatch.core.settings import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(
        str(settings.redis_url),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )
