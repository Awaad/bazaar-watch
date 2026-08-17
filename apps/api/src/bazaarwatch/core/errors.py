"""RFC 9457 problem details.

`code` is the contract and is what clients branch on. `title` and `detail` are
human-facing and may change without a version bump.

See docs/04-api-contracts.md section 5.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_BASE_URI = "https://bazaarwatch.dev/errors"
PROBLEM_CONTENT_TYPE = "application/problem+json"


class ErrorCode(StrEnum):
    """Generated into packages/api-types. Removing a member is a breaking
    change under contract-diff (ADR-0042)."""

    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    UPGRADE_REQUIRED = "UPGRADE_REQUIRED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INTERNAL = "INTERNAL"


class ProblemError(Exception):
    """Raised anywhere; rendered once by the handler registered in the app
    factory."""

    def __init__(
        self,
        *,
        code: ErrorCode,
        status: int,
        title: str,
        detail: str | None = None,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(title)
        self.code = code
        self.status = status
        self.title = title
        self.detail = detail
        self.errors = errors or []

    def to_dict(self, instance: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": f"{PROBLEM_BASE_URI}/{self.code.value.lower().replace('_', '-')}",
            "title": self.title,
            "status": self.status,
            "code": self.code.value,
        }
        if self.detail is not None:
            body["detail"] = self.detail
        if instance is not None:
            body["instance"] = instance
        if self.errors:
            body["errors"] = self.errors
        return body


async def problem_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)
    return JSONResponse(
        status_code=exc.status,
        content=exc.to_dict(instance=request.url.path),
        media_type=PROBLEM_CONTENT_TYPE,
    )
