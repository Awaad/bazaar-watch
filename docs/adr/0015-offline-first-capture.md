# ADR-0015: Offline-first capture with at-least-once sync

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Supermarket interiors have poor mobile signal. Capture happens exactly where the network
is worst.

A capture lost to a failed request is worse than a slow one, because the contributor is no longer
standing in the shop and cannot repeat it.

At-least-once delivery is the only honest assumption for a mobile client on an unreliable network.

## Decision

Every capture is durable local state first and a network operation second, using
`expo-sqlite` rather than key-value storage, because a queue needs transactions, ordering and
survival across force-quit.

Each queued item carries a `client_idempotency_key` generated at capture time, which is an opaque
v4 token and never a primary key (ADR-0003).

Sync retries with exponential backoff and jitter, drains on connectivity, on foreground and on user
request, and never blocks capture.

Media upload is two-phase and resumable (ADR-0070). A confirmed object is never re-uploaded, because
the content hash makes the duplicate detectable server-side.

Every mutating endpoint accepts `Idempotency-Key`. Replay with the same body returns the original
response; replay with a different body returns `409`.

## Consequences

Contributions survive a dead network, a killed app and a flat battery.

Idempotency is mandatory rather than defensive, and its absence on any mutating endpoint is a bug.

The client maintains local identifiers mapped to server identifiers on sync response.

A queue that has not drained in 24 hours exceeds the idempotency replay window, which is accepted
because a queue stuck that long has a worse problem than replay.

## Alternatives considered

**Online-only capture.** Rejected. Loses captures precisely where capture happens.

**AsyncStorage or similar key-value store.** Rejected. Not a queue; no transactions, no ordering
guarantees.

**Exactly-once delivery.** Rejected as unachievable over an unreliable network. Idempotency makes
at-least-once safe, which is the standard answer.

## Revisit trigger

Never, absent a change in how the app captures.
