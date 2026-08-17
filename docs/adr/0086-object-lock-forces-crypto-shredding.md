# ADR-0086: Object lock is what forces crypto shredding

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Crypto shredding adds real complexity: envelope encryption, a key store, key lifecycle, and
a backup constraint that is easy to break silently (ADR-0072).

A simpler alternative exists. Versioning plus cross-provider replication would permit genuine
deletion and need no key store at all. Erasure would mean deleting across replicas and versions.

The reason this is not chosen is worth recording explicitly, because the simpler option will look
attractive to anyone reviewing the design later.

## Decision

Object lock on originals (ADR-0069) makes physical deletion impossible before expiry, so
key destruction is the only mechanism compatible with the corpus guarantee.

The decisive argument is **evidentiary rather than architectural**: a destroyed key is demonstrable,
whereas proving that every copy across every replica and every version was reached is not. Erasure is
an obligation that may have to be shown, not merely performed.

Build complexity is a one-time cost. Execution reliability is forever.

If legal review rejects crypto shredding, the fallback is to drop object lock in favour of
versioning, accepting a weaker corpus guarantee (ADR-0074).

## Consequences

The complexity is justified by a stated reason that survives review rather than
looking like over-engineering.

The fallback position and its cost are identified in advance.

The corpus guarantee and the erasure guarantee are both strong, which is unusual and is the point.

Anyone proposing to simplify by removing the key store must first address the object lock and the
demonstrability argument.

## Alternatives considered

**Versioning plus multi-replica deletion.** Rejected. Simpler to build, fragile to
execute, and hard to demonstrate.

**No object lock, ordinary deletion.** Rejected. Weakens the corpus guarantee that the reprocessing
strategy depends on.

**Object lock with a short retention that expires before erasure requests arrive.** Rejected. Erasure
requests can arrive at any time, so no lock period is safe.

## Revisit trigger

Object lock is removed from originals, which would remove the forcing constraint.
