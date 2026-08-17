# ADR-0069: Originals are a strategic asset and must be backed up

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Originals are usually thought of as evidence for disputes. They are more than that: the
entire reprocess-when-the-model-improves strategy (ADR-0013, ADR-0082) depends on them surviving.

Extraction quality will improve substantially over the project's life, and the ability to re-run it
across the whole corpus is the largest single lever on data quality available.

Object storage is durable but not backed up. Durability protects against hardware failure. It does
not protect against a bug, a compromised credential, or an account-level problem deleting things.

## Decision

Originals carry versioning, object lock, and cross-provider replication.

Cross-provider rather than cross-region, because the corpus is irreplaceable and small, and
account-level loss is a real failure mode that cross-region replication does not cover.

Crops are not replicated with the same guarantees, since they are derived and regenerable from
originals.

Backup restoration is verified on a schedule, because an untested backup is a hypothesis.

## Consequences

The reprocessing strategy is safe, which is what makes the versioned extraction
design meaningful rather than aspirational.

Object lock means objects cannot be deleted before expiry, which is precisely the constraint that
forces crypto shredding for erasure (ADR-0086).

Storage cost roughly doubles for originals. Small in absolute terms and clearly worth it.

Lifecycle rules interact with object lock and with retention, so the retention answer changes the
configuration but not the principle.

## Alternatives considered

**Rely on provider durability.** Rejected. Durability is not backup and does not cover
deletion.

**Cross-region replication within one provider.** Rejected. Does not cover account-level loss, which
is the failure mode that would be unrecoverable.

**Discard originals after a short window.** Rejected. Destroys reprocessing, the main quality lever,
and the evidence behind disputed observations.

## Revisit trigger

Corpus size grows enough that replication cost becomes material, which would take a very
long time at receipt image sizes.
