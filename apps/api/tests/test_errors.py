from __future__ import annotations

from bazaarwatch.core.errors import ErrorCode, ProblemError


def test_problem_shape_matches_rfc_9457() -> None:
    problem = ProblemError(
        code=ErrorCode.CONFLICT,
        status=409,
        title="Submission already received",
        detail="A submission with this idempotency key was already accepted.",
        errors=[{"field": "client_idempotency_key", "code": "DUPLICATE"}],
    )
    body = problem.to_dict(instance="/v1/submissions")

    assert body["status"] == 409
    assert body["code"] == "CONFLICT"
    assert body["type"].endswith("/conflict")
    assert body["instance"] == "/v1/submissions"
    assert body["errors"][0]["field"] == "client_idempotency_key"


def test_optional_fields_are_omitted_rather_than_null() -> None:
    body = ProblemError(code=ErrorCode.NOT_FOUND, status=404, title="Not found").to_dict()
    assert "detail" not in body
    assert "instance" not in body
    assert "errors" not in body
