# ADR-0058: Route review on residual, disagreement and novelty, never on self-reported confidence

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The obvious way to decide which lines need human eyes is to route on the extractor's
confidence score.

That fails on exactly the cases that matter. A generative model reading a faded `45.90` as `46.90`
reports high confidence, because it is producing plausible text rather than recognising glyphs. The
dangerous errors are precisely the ones the model does not flag.

Better signals exist and are free.

## Decision

Routing signals, in order of strength:

**Reconciliation residual.** If lines fail to sum to the total by a specific amount, that amount
points at the error. A residual of exactly 1.00 lets candidate lines be ranked by which single digit
flip would close the gap. This is the most precise routing signal available and it costs nothing.

**Dual-extractor disagreement** on price fields above a value threshold.

**Novelty**: a raw key never seen at that chain needs eyes regardless, and this is what generates T1
tasks.

**Image quality**: blur, skew and contrast measured on the specific region.

Self-reported confidence is recorded and is never a routing signal on its own.

## Consequences

Review effort concentrates where it is most likely to find something, rather than
where a model happens to feel uncertain.

Reconciliation correctness is load-bearing for routing as well as for integrity, which is why the KDV
treatment warranted its own record (ADR-0081).

Residual-based candidate ranking is a small amount of arithmetic with a disproportionate payoff.

Receipts that reconcile perfectly generate no T2 tasks, so a hallucination that happens to balance
goes unreviewed. That gap is real and is covered only by corroboration.

## Alternatives considered

**Route on model confidence.** Rejected. Uncorrelated with correctness on hard cases.

**Route everything to review.** Rejected. Defeats the purpose.

**Route randomly at a sampling rate.** Rejected as a primary mechanism, though useful as a small
background sample for measuring extraction quality.

## Revisit trigger

A provider ships calibrated per-field confidence demonstrated to correlate with correctness
on the bake-off set.
