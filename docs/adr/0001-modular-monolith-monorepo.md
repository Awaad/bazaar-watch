# ADR-0001: Modular monolith in a monorepo

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Six deployables are required: an API, an inference worker, a scheduler, two Next.js
surfaces and an Expo client. The work is carried out by parallel workstreams, frequently by
different agents, against a specification that is still moving.

The genuinely hard problems in this project are entity resolution on receipt text, integrity
under high price dispersion, and a defensible index methodology. Service topology is not one of
them. Distributed architecture would consume attention those problems need, and the service
boundaries cannot be drawn correctly yet because the domain is not yet understood well enough.

## Decision

One monorepo. One FastAPI deployable containing all domain modules. Module boundaries
enforced by `import-linter` in CI rather than by convention.

Exactly one process split: the inference worker (ADR-0043).

Modules own their tables. Cross-module access goes through service layers, never by importing
another module's SQLAlchemy models. Dependency direction is downward only, with no cycles.
Sequencing that crosses modules lives in a `workflows/` layer which may import any module and
which no module may import.

## Consequences

A boundary violation fails the build rather than producing a review comment, so
boundaries hold under agent-driven development where review attention is thin.

Extracting a module later is cheap because the seam is already enforced. The cost of keeping the
seam is close to zero; the cost of recreating it after erosion is not.

A single deployable means a Postgres outage is a full outage. Accepted (ADR-0002).

`workflows/` is a real layer with real rules, not a convenience. Domain logic leaking into it
would recreate the coupling the module laws exist to prevent.

## Alternatives considered

**Microservices.** Rejected. Service boundaries drawn before the domain is
understood would be wrong, and inter-service contracts, tracing and deployment would consume the
window that the hard problems need.

**Multiple repositories.** Rejected. Contract generation across repository boundaries adds
release coordination that a monorepo makes unnecessary.

**No enforced boundaries.** Rejected. Conventions erode, and they erode fastest under parallel
work by contributors who did not write the convention.

## Revisit trigger

A module requires an independent scaling profile or deploy cadence, evidenced by
measurement rather than anticipation.
