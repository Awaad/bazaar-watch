"""Application settings.

Read from the environment. Nothing carries a default that would be wrong in
production: a missing database URL fails at startup rather than falling back to
something that happens to be correct on one machine.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Environment = Environment.LOCAL

    database_url: PostgresDsn = Field(
        description="SQLAlchemy async DSN, postgresql+psycopg://...",
    )
    redis_url: RedisDsn = Field(
        description="Redis DSN. Job queue, rate limits, idempotency records.",
    )

    api_port: int = 58000

    # Echoing SQL is a development convenience and a production liability: it
    # writes query parameters, which include personal data, into the log.
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 5

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read once. Reading per request would let the process change behaviour
    mid-flight, which is harder to reason about than a restart."""
    return Settings()  # type: ignore[call-arg]
