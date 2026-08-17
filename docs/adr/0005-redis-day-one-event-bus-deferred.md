# ADR-0005: Redis from day one; domain event bus deferred

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Rate limiting, idempotency replay storage, distributed locks and the job queue all
require a fast shared store. The extraction pipeline needs a queue regardless of any other
consideration.

A transactional outbox with a domain event bus is a well-understood pattern for decoupling
modules asynchronously. It is also machinery that only pays for itself when cross-module async
consumers exist.

At present no module needs to react asynchronously to another module's state change. The
ingestion pipeline is a linear sequence orchestrated by the `workflows/` layer.

## Decision

Redis is day-one infrastructure for cache, rate limiting, locks and the Celery job
queue.

The transactional outbox and a domain event bus are **deferred**. The seam is preserved by
keeping cross-module sequencing in `workflows/`, so introducing events later does not require
restructuring modules.

## Consequences

One less pattern to build, operate and reason about during the phase when the
domain is least understood.

Redis unavailability means writes that enqueue jobs fail with `503`, while reads continue. Redis
eviction above zero is an alert condition, because it means rate limits and idempotency keys are
being silently dropped.

If a genuine async consumer appears, adding an outbox is additive work rather than a
restructuring, because module boundaries already prevent direct cross-module calls.

## Alternatives considered

**Outbox and event bus from the start.** Rejected as machinery serving a
requirement that does not exist, during the window when attention is scarcest.

**No Redis, database-backed queue.** Rejected. Rate limiting and idempotency both want a fast
shared store, and a database queue would put contention on the hottest tables.

## Revisit trigger

A module needs to react to another module's state change without the `workflows/` layer
coordinating it, or a second consumer appears for an existing state transition.
