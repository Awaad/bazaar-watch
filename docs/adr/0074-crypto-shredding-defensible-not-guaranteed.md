# ADR-0074: Crypto shredding is defensible, not guaranteed

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Crypto shredding is widely used and widely accepted as a means of honouring erasure where
physical deletion is impractical.

It is not universally settled. Some supervisory authorities have questioned whether strongly
encrypted data with a destroyed key is fully erased, on the reasoning that the ciphertext still
exists and cryptographic assumptions can weaken over time.

Presenting it internally as a settled guarantee would be a misrepresentation that surfaces at exactly
the wrong moment.

## Decision

Crypto shredding is recorded as defensible practice, not as a formal guarantee.

The reasoning is documented so that it can be presented to a regulator or an auditor: object lock
makes physical deletion impossible, key destruction is the available mechanism, and it is
demonstrable in a way that multi-replica deletion is not (ADR-0086).

If legal review requires physical deletion, the alternative is to remove object lock from originals
in favour of versioning, accepting a weaker corpus guarantee. That trade is identified in advance
rather than discovered under pressure.

## Consequences

The documentation is honest about the residual risk, which is what makes it useful in
an assessment.

A fallback position exists and its cost is known.

The team is not surprised if a regulator pushes back.

There is no operational difference from treating it as guaranteed; the difference is in what is
claimed.

## Alternatives considered

**Claim full erasure without qualification.** Rejected. Overstates a contested
position.

**Avoid crypto shredding entirely because it is contested.** Rejected. The alternative is weaker in
practice and harder to demonstrate.

**Seek a formal opinion before building.** Reasonable, and it is the substance of the open legal
review. It does not block the architecture, since the fallback is a configuration change.

## Revisit trigger

Regulatory guidance clarifies the position in either direction.
