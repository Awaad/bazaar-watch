# ADR-0048: Reviewer independence, not bridging-based ranking

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Community Notes is the obvious reference model, and its central mechanism is bridging-based
ranking: a note surfaces only when rated helpful by people who normally disagree with each other.

That mechanism exists because its ground truth is contested along an ideological axis and its failure
mode is brigading.

Neither applies here. A receipt line objectively does or does not say 45.90, and there is no
ideological axis to bridge across.

The failure mode that does apply is collusion: a submitter and a reviewer acting together.

## Decision

Reviewer **independence** from the submitter, not bridging.

A reviewer never receives a task tracing to their own submission, or to a submitter with whom they
share a referral link, a device fingerprint, or a history of mutual review.

This is enforced in the `integrity` service at task assignment, because it cannot be expressed as a
database constraint, and it therefore requires direct adversarial test coverage.

## Consequences

Simpler and better matched to the problem than bridging, which would require modelling
a disagreement axis that does not exist.

Assignment becomes a filtered query rather than a simple queue pop, which has a cost as the
contributor base grows.

In a very small contributor base, independence constraints may leave a task with no eligible
reviewer, which must escalate to an operator rather than relax the rule.

Device fingerprinting is itself a privacy-relevant signal and must be handled accordingly.

## Alternatives considered

**Bridging-based ranking.** Rejected. Solves a problem this domain does not have.

**Simple majority vote.** Rejected. Trivially defeated by collusion, which is the actual threat.

**No independence constraint.** Rejected. Validation would be theatre.

**Random assignment only.** Rejected. Random assignment does not prevent collusion, it only makes it
slower.

## Revisit trigger

Contributor base grows large enough that independence filtering becomes expensive, at which
point the filter needs indexing rather than relaxing.
