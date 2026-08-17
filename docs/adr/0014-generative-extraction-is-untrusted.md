# ADR-0014: Generative extraction output is treated as untrusted input

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A generative model reading a faded `45.90` as `46.90` reports high confidence, because it
is producing plausible text rather than recognising glyphs. This is categorically different from
classical OCR, which degrades toward low-confidence or garbage rather than toward confident fiction.

Silent numeric corruption in a price database is the worst available failure mode. It passes review,
enters the index, and is discovered only if someone happens to check against the original.

## Decision

Extraction output is validated, never trusted.

Defences, in order of strength:
1. **Arithmetic reconciliation.** Item lines minus discounts must equal the printed total
   (ADR-0081). This catches most single-digit errors for free.
2. **Dual-extractor disagreement** on price fields above a value threshold. Two models disagreeing
   is a far better signal than either model's self-reported confidence.
3. **Targeted human review** on residual or disagreement (ADR-0058).

Self-reported confidence is recorded but is never a routing signal on its own.

## Consequences

Reconciliation is promoted from a nice check to the primary integrity mechanism, and
a change in its correctness (such as the KDV treatment) breaks the whole defence.

Dual extraction costs roughly double on the receipts it is applied to, so it is applied selectively
by value rather than universally.

Some corruption will still get through: a hallucinated price on a receipt that happens to reconcile
is undetectable by arithmetic. Corroboration from independent contributors at the same branch is the
only remaining defence, which is a coverage problem before it is an integrity problem.

## Alternatives considered

**Trust provider confidence.** Rejected. Uncorrelated with correctness on exactly the
hard cases.

**Human-review everything.** Rejected. Does not scale, and is the bottleneck the system exists to
avoid.

**Dual extraction on all receipts.** Rejected on cost. Applied by value threshold instead.

## Revisit trigger

A provider ships calibrated per-field confidence that is demonstrated to correlate with
correctness on the bake-off set.
