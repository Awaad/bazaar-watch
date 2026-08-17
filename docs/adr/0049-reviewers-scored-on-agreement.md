# ADR-0049: Reviewers are scored on eventual agreement, never on volume

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

If reviewing earns points per task completed, the optimal strategy is to approve everything
as fast as possible. The reviewer who does least thinking earns most.

That produces a rubber stamp: bad data passes through community review and emerges with a veneer of
validation, which is worse than no review because it creates false confidence.

Scoring on agreement solves it, but agreement with what is not obvious. Waiting for eventual
corroboration means a new reviewer has no score for a long time.

## Decision

Reviewer weight derives from agreement with ground truth, meaning later corroboration,
operator adjudication, or a honeypot answer (ADR-0061).

`contributor_trust.review_weight` starts low from tuning, rises with demonstrated accuracy, and
decays for indiscriminate approval.

`review_responses.weight` snapshots the weight at answer time, so a later trust recomputation cannot
retroactively rewrite a past decision.

Review earns points, but small fixed amounts, and only when the task reaches quorum with the reviewer
in agreement.

Trust values are internal and never serialised to a client.

## Consequences

Approving everything becomes worthless rather than optimal.

Honeypots are load-bearing rather than a nicety, since they are what gives a new reviewer a score in
their first session.

Weight snapshotting means historical decisions are stable and auditable.

A reviewer whose weight decays to near zero is effectively excluded without ever being told they were
wrong, which needs care in how it is communicated.

## Alternatives considered

**Points per review completed.** Rejected. Builds a rubber stamp.

**No reward for reviewing.** Rejected. Review is real work and unrewarded work does not happen at
volume.

**Publish reviewer accuracy publicly.** Rejected. Exposes the scoring function and invites gaming,
and public accuracy shaming is a poor community dynamic.

## Revisit trigger

Measured review agreement rates show the weighting is not discriminating between careful
and careless reviewers.
