# ADR-0061: Honeypots give immediate reviewer scoring

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Reviewer weight derives from agreement with ground truth (ADR-0049). Ground truth normally
arrives late, through corroboration or operator adjudication.

That leaves a new reviewer unscored for a long time, during which their answers must either be
weighted at a default or discounted entirely. Both are unsatisfying: the first admits unmeasured
reviewers into quorum, the second wastes their work.

A reviewer who intends to farm points has a long unmeasured window in which to do it.

## Decision

Tasks with known answers are injected into the review queue.

They are drawn from previously adjudicated tasks, so they are indistinguishable from real work.

They produce an accuracy signal immediately, from a reviewer's first session rather than their
fiftieth.

Injection rate is a tuning parameter (ADR-0021). Honeypot status is never serialised to a client, and
`review_tasks.is_honeypot` carries a constraint requiring an expected answer.

## Consequences

Reviewer weight is meaningful early, which makes the whole trust mechanism work at
small scale.

Farming is detected quickly rather than after damage.

Some reviewer effort goes into tasks that produce no new information, which is the cost of
measurement.

Honeypots must be refreshed as the adjudicated pool grows, or a regular reviewer starts recognising
them.

## Alternatives considered

**Wait for eventual corroboration only.** Rejected. Leaves new reviewers unmeasured
for too long, which is exactly the window an abuser needs.

**Synthetic honeypots.** Rejected. Generated tasks look different from real ones and would be
identifiable.

**Weight all new reviewers at zero until proven.** Rejected. Wastes their work and gives no path to
proving anything.

## Revisit trigger

Honeypot pass rates stop discriminating, suggesting reviewers have learned to recognise
them.
