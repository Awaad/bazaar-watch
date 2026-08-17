# ADR-0059: One line per receipt per reviewer

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A single cropped line leaks nothing. It shows a product and a price, which is unremarkable.

Many crops from one receipt are a different matter. Together they reconstruct the basket, and basket
composition supports inferences about health, religion, pregnancy and alcohol use.

The tiered review design (ADR-0057) makes PII structurally absent from any individual crop, and
aggregation defeats that if it is not prevented.

## Decision

No reviewer receives more than one line from a given receipt.

`review_tasks` carries `receipt_id` even for T1 tasks, so the rule is checkable in a single query
rather than requiring a join back through observations.

Enforced in the `integrity` service at assignment, because it cannot be expressed as a database
constraint, and therefore requiring direct adversarial test coverage.

## Consequences

Basket reconstruction through the review surface is prevented structurally.

Assignment is a filtered query rather than a queue pop, and the filter grows with a reviewer's
history.

A receipt with many uncertain lines needs many distinct reviewers, which is a throughput cost in a
small contributor base and may leave tasks unassignable until it grows.

Unassignable tasks escalate to an operator rather than relaxing the rule.

## Alternatives considered

**No limit.** Rejected. Defeats the entire tiered design.

**Limit to a small number rather than one.** Rejected. Any number above one permits partial
reconstruction, and the threshold would be arbitrary.

**Randomise which lines a reviewer sees across receipts.** Rejected. Does not prevent aggregation, it
only makes it slower.

## Revisit trigger

Never, while crops are shown to non-operators.
