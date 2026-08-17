# ADR-0042: Contracts are generated, never hand-written

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Two clients and a public web surface consume one API, and those workstreams run in parallel,
frequently by different agents, against a specification that is still moving.

Contract drift is therefore the primary engineering risk in this project. A hand-maintained
specification eventually lies about the implementation, and a specification that lies is worse than
none because both clients trust it.

Drift usually enters through a status string rather than through a shape, which type generation alone
does not catch.

Client work cannot wait for endpoints to exist without serialising the workstreams.

## Decision

`openapi.json` is emitted from the FastAPI application, committed, and diffed in CI. It is
never authored by hand.

TypeScript types, clients, enums, constants and error codes are generated from it into
`packages/api-client-ts` and `packages/api-types`. Generated directories are committed so a diff is
visible in review, and never hand-edited.

A mock server is generated from the specification, so client workstreams build and test before
endpoints exist.

`/v1` from the first commit; additive change only within it.

CI gates: `openapi-fresh`, `contract-diff` against the merge base, `client-fresh`,
`no-handwritten-calls`, `enum-parity` against database `CHECK` constraints.

## Consequences

Parallel agent-driven development is safe, which is what makes the delivery model
viable at all.

A breaking change cannot be introduced silently, and `contract-diff` compares against the merge base
rather than the previous commit, which would give false passes on any multi-commit branch.

Enumerations have a single definition as a Python `StrEnum` flowing to OpenAPI, TypeScript and the
database constraint.

Adding an endpoint means regenerating and committing in the same change, so pull requests are larger
and show exactly what clients will see.

## Alternatives considered

**Hand-written OpenAPI as the source of truth.** Rejected. It drifts from the
implementation and both clients trust it.

**Hand-written clients.** Rejected. Drift with no detection mechanism.

**Generated but not committed.** Rejected. CI could not fail on staleness and reviewers could not see
the effect of a change.

**No mock server.** Rejected. It would serialise client work behind backend work.

## Revisit trigger

Never, while more than one client consumes the API.
