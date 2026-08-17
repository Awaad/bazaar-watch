# ADR-0067: S3 API, not a provider SDK

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Object storage providers offer their own SDKs with provider-specific features. Using one
couples the application to that provider.

Storage is the one dependency where the data cannot easily be moved once it is large, so lock-in has
a real cost.

Every serious provider offers an S3-compatible API, and the operations needed here are basic: put,
get, delete, presign, lifecycle, versioning.

Cost varies mainly on egress, which is small for crops and internal for originals.

## Decision

Access object storage through the S3 API via boto3. The provider is a configuration
value.

Hetzner Object Storage as the default, since same-network transfer is cheap and latency to Cyprus is
good given the application is hosted there.

Cloudflare R2 if egress ever becomes material, which is unlikely at crop sizes.

Self-hosted MinIO is declined: operational surface bought for nothing.

## Consequences

Provider change is a configuration change plus a data migration, not a code change.

Provider-specific features are unavailable, which is acceptable because none are needed.

Cross-provider replication for originals (ADR-0069) is straightforward, since both ends speak the
same API.

Presigned URL semantics differ slightly between implementations, which needs verification rather than
assumption when a provider changes.

## Alternatives considered

**Provider SDK.** Rejected. Lock-in on the dependency where lock-in costs most.

**Self-hosted MinIO.** Rejected. Adds backup, monitoring and availability responsibility for a solo
operation, replacing a solved problem with an unsolved one.

**Local filesystem storage.** Rejected. No replication, no versioning, no object lock, and it ties
media to a single host.

## Revisit trigger

A provider-specific capability becomes genuinely necessary, or egress economics change
materially.
