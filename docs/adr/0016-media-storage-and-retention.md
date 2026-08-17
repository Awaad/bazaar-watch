# ADR-0016: Media storage separate from the database, with originals retained

**Status:** Accepted
**Accepted:** 2026-08-17
**Open parameter:** Retention window, pending legal review. The storage architecture and the decision to retain originals are settled.
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Receipt images are multi-megabyte binaries. They are also the reprocessing corpus on which
ADR-0013 and ADR-0069 depend.

Cropping for review (ADR-0057) does not replace the original. Originals retain date, branch and store
name evidence, and remain the only artefact against which a disputed extraction can be checked.

Retention duration is a legal question that has not been answered.

## Decision

Receipt images go to object storage, never to the database. Storage architecture is
specified in ADR-0063 through ADR-0070.

Originals are retained as the reprocessing corpus, subject to a retention window to be set once legal
review completes.

`media_objects` records bucket, key, content hash, dimensions, re-encoding status, and the subject
whose key wraps the object.

Retention gates only the lifecycle policy and T3 full-receipt review. T1 and T2 community review
expose no PII by construction and do not wait on it (ADR-0057).

## Consequences

Database size stays proportional to structured data rather than to image volume.

The corpus can be reprocessed as extraction improves, which is the largest single quality lever over
the project's life.

An unanswered legal question blocks the lifecycle policy but not the product, because the review
tiering removed the dependency.

Originals require object lock, versioning and cross-provider replication, which is real cost for an
asset that is irreplaceable.

## Alternatives considered

**Images in the database as bytea.** Rejected. Bloats backups, WAL and restore time
for no benefit.

**Discard originals after extraction.** Rejected. Destroys reprocessing, which is the main quality
lever, and removes the evidence behind every disputed observation.

**Keep only crops.** Rejected. Crops are derived from a specific extraction run and cannot be
regenerated for lines that run did not identify.

## Revisit trigger

Legal review returns a retention answer.
