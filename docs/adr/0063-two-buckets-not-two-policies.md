# ADR-0063: Two buckets, not one bucket with two policies

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Originals and crops have genuinely different exposure profiles. Originals carry PII and go
only to operators and the worker. Crops are PII-free by construction and go to contributors.

The obvious implementation is one bucket with per-object access control. Object-level ACLs are also
the thing that gets misconfigured, and a misconfiguration here exposes complete baskets rather than
a wrong price.

The tiered review design (ADR-0057) established the principle: make the dangerous thing absent
rather than check for it. The same principle applies one layer down.

## Decision

Two physically separate buckets with different policies.

`receipts-original`: never public, no contributor URL ever, object lock, versioned, cross-provider
replicated, written by the worker only.

`receipts-crop`: never public, served through the API for per-request authorization and audit,
written by the worker only.

Bucket-level policy rather than per-object ACL, because bucket policy is far harder to get
accidentally wrong and easier to verify at a glance.

## Consequences

A misconfiguration affects a whole bucket, which is loud and detectable, rather than
a single object, which is silent.

Credentials can be scoped per bucket, which is what makes capability isolation possible (ADR-0064).

Two lifecycle policies to maintain rather than one, with different retention rules.

Crops must be regenerable from originals, since they are derived and their bucket is not replicated
with the same guarantees.

## Alternatives considered

**One bucket, per-object ACLs.** Rejected. The failure mode is silent and the blast
radius is complete basket data.

**One bucket, prefix-based policy.** Rejected. Weaker than bucket boundaries and easy to defeat with
a wrong key.

**Crops in the database as bytea.** Rejected. Small enough to be tempting, but it puts binary data
in backups and WAL for no benefit.

## Revisit trigger

Never, while originals and crops have different audiences.
