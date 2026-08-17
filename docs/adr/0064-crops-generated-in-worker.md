# ADR-0064: Crops are pre-generated in the worker; the API holds no credential for originals

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Crops could be generated on demand when a review task is served. That would require the
API to read the original, which means the API needs a credential for the originals bucket.

Once the API can reach originals, every authorization bug in the request path becomes a potential
exposure of complete receipt images.

The worker already has the original open during extraction, so generating crops there costs nothing
additional.

## Decision

Crops are pre-generated in the worker during extraction and written to `receipts-crop`.

The `api` process holds **no credential** for `receipts-original` at all.

| Process | `receipts-original` | `receipts-crop` |
|---|---|---|
| `api` | none | read |
| `worker` | read/write | write |

Operator access to originals is mediated: the console requests a short-TTL signed URL from an
`/v1/ops/*` endpoint, which the worker mints.

Crops are generated for lines routed to review, not for every line.

## Consequences

An entire class of authorization bug becomes impossible rather than merely guarded
against, which is the strongest form of this kind of control.

Review queue serving is fast, since crops already exist.

Crops are tied to a specific extraction run. A re-extraction that identifies different line
boundaries needs new crops, and old ones become orphaned rather than wrong.

The worker becomes a dependency for operator access to originals, which is an availability
consideration.

## Alternatives considered

**Generate crops on demand in the API.** Rejected. Requires giving the API a
credential it must not have.

**Generate crops in a third process.** Rejected. The worker already has the file open; a third
process adds a deployable for nothing.

**Serve originals to reviewers with client-side cropping.** Rejected. The full image would be
delivered to the client, defeating the entire tiered design.

## Revisit trigger

Never, while non-operators see any part of a receipt image.
