# ADR-0077: Class mean imputation, never carry-forward

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A branch will lack a recent observation for some basket items in some periods. Something
must fill the gap or the index cannot be computed.

The intuitive answer is to repeat last period's price. It is what naive implementations do, and it
is wrong in a specific and damaging way: it systematically dampens the index toward zero change.

Under high inflation, dampening toward zero is precisely the wrong bias. It would make the index
understate exactly what it exists to measure.

## Decision

Missing relatives are imputed by **class mean imputation**: the missing price relative is
imputed from the mean relative of its elementary class in the same period.

**Carry-forward is not used.**

`index_runs.missing_policy` records the policy applied, and `index_values.imputed_pct` is published
alongside every value.

A figure resting largely on imputation is disclosed as such rather than presented as measurement, and
values below a coverage floor are suppressed entirely (ADR-0029).

## Consequences

The index tracks actual price movement rather than being pulled toward zero by
gaps.

Imputation share becomes a published quality metric and an operational target, which is one of the
levers bounties exist to move (ADR-0020).

Class mean imputation requires the elementary class to have some observations, so a class with no
coverage at all cannot be imputed and must be suppressed.

The method must be stated publicly, since imputation choices are exactly what a critic examines.

## Alternatives considered

**Carry-forward.** Rejected. Systematic downward bias in the measurement that matters
most.

**Drop missing items from the basket for that period.** Rejected. Changes the basket period to
period, which breaks comparability.

**Target mean imputation from a similar branch.** Not rejected on merit, and it is arguably better
where a comparable branch exists. Deferred as a refinement because it requires a defensible
similarity definition.

## Revisit trigger

Coverage improves enough that imputation becomes rare, or a defensible branch-similarity
measure makes target mean imputation preferable.
