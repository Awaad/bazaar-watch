"""Structured logging.

JSON, one event per line. Redaction happens at the processor rather than by
choosing a log level, so a sensitive field cannot leak because someone raised
verbosity during an incident.

See docs/14-observability-analytics.md section 1.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

# Never logged, at any level. Signed URLs matter particularly: a log aggregator
# turns a short-TTL credential into a durable one.
REDACTED_KEYS = frozenset(
    {
        "phone",
        "phone_e164",
        "otp",
        "code",
        "token",
        "access_token",
        "refresh_token",
        "password",
        "authorization",
        "signed_url",
        "upload_url",
        "kek_ref",
        "wrapped_dek",
        "capture_location",
        "latitude",
        "longitude",
    }
)

_REDACTED = "[redacted]"


def _redact(
    _logger: object, _name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    for key in list(event_dict):
        # Log field names are ASCII identifiers, never user text.
        if key.lower() in REDACTED_KEYS:  # gate-ignore: naive-casing
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(*, json_output: bool) -> None:
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)
