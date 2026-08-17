# ADR-0043: One process split: the inference worker

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Extraction and embedding have a genuinely different profile from HTTP serving: CPU-bound,
memory-hungry, long-running, batch-friendly, with a multi-gigabyte dependency tree.

Loading a model into the API container bloats every request-serving instance, slows cold starts, and
scales the wrong axis when receipts spike.

Splitting for architectural interest, on the other hand, would consume attention the genuinely hard
problems need, and service boundaries cannot be drawn correctly before the domain is understood.

## Decision

Exactly one split: a Celery worker running extraction, crop generation and embedding
generation.

It is a **queue consumer**, not a service. No API, no message bus, no synchronous contract. It reads
jobs from Redis and writes results to Postgres.

Everything else stays in the monolith behind enforced module boundaries (ADR-0001).

The split carries a second benefit that turns out to matter more than performance: the worker is the
only process holding a credential for the originals bucket, so capability isolation falls out of it
(ADR-0064).

## Consequences

One additional deployable and close to zero conceptual complexity, since there is no
inter-service contract to version.

The worker scales independently, which is the correct axis under load.

Prefork suits CPU-bound inference naturally, which is why Celery was chosen over an asyncio-native
queue that would need executor gymnastics for exactly this workload.

Beat must run as exactly one instance, or scheduled index runs duplicate.

## Alternatives considered

**Model inference inside the API process.** Rejected. Bloated images, slow cold
starts, wrong scaling axis, and it would give the API a credential it must not have.

**Inference as an HTTP microservice.** Rejected. Adds a synchronous contract and a failure mode for
no benefit over a queue.

**Split search, catalog or ingest as services.** Rejected. Service topology is not a hard problem
here, and the boundaries cannot yet be drawn correctly.

**External inference API only.** Not rejected; the provider interface allows it. The worker still
exists for crop generation and orchestration.

## Revisit trigger

A second workload appears with a genuinely different resource profile, which is the same
test that justified this split.
