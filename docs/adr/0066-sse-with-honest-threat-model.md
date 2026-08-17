# ADR-0066: Server-side encryption at rest, with an honest threat model

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Encryption at rest is easy to enable and easy to over-claim. It is often cited as though it
protects against unauthorised access generally.

It protects against disk-level compromise and certain provider-side scenarios. It does **not**
protect against a leaked API credential, because the provider decrypts transparently for anyone
holding a valid key.

A leaked credential is the realistic threat here, not physical disk theft.

Application-level encryption would defeat a credential leak, but it breaks server-side image
processing and adds key management that a small operation should not own for general storage.

## Decision

Server-side encryption with provider-managed keys is enabled on both buckets. It is free
and there is no reason not to.

It is documented as **not** the protection that matters. What protects the corpus is credential
scoping per process (ADR-0064), rotation, and bucket policy.

Application-level encryption is declined for general storage. Envelope encryption is used only where
it serves a purpose SSE cannot: crypto shredding for erasure (ADR-0071).

## Consequences

No false comfort in the documentation, which matters when someone later assesses the
security posture.

Effort goes to credential hygiene, which is where the actual risk is.

Server-side image processing continues to work, since the provider decrypts transparently for the
worker.

The distinction between SSE and the erasure envelope encryption must be clear, or someone will
conclude one makes the other redundant.

## Alternatives considered

**Application-level encryption for all objects.** Rejected. Breaks processing, adds
key management, and the erasure use case is served by a narrower mechanism.

**No encryption at rest.** Rejected. It is free and covers a real if narrower threat.

**Customer-managed keys for SSE.** Available and not chosen now. It adds rotation control without
changing the credential-leak exposure.

## Revisit trigger

Legal review requires customer-managed keys or stronger, or a provider-side incident
changes the threat assessment.
