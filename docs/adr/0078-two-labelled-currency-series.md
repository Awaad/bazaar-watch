# ADR-0078: Two labelled currency series, never one blended number

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Northern Cyprus runs on multiple currencies. Many residents earn in TRY, and a substantial
population earns in GBP, EUR or USD.

TRY inflation and TRY depreciation are different phenomena with different effects on different
households. A TRY-earning household experiences TRY price rises as inflation, full stop. A
foreign-currency earner experiences something quite different.

Blending them into one number would serve neither and would be indefensible to both.

An index of price relatives with a base of 100 is by construction immune to the nominal-level
confusion that makes raw price comparison across time misleading, which resolves part of the
problem.

## Decision

Two labelled series, distinguished by `index_values.series_basis`.

**`try_nominal`** is the primary series, because TRY inflation is what a TRY-earning household
experiences and it is the conventional measure.

**`fx_deflated`** is secondary, using recorded rates from `fx_rates` with their `as_of` dates so any
published value is reproducible.

Neither is presented as the real one. They answer different questions for different households.

## Consequences

Both audiences get a figure that means something for them.

`fx_rates` becomes a published input, so rate source and timing are part of the methodology rather
than an implementation detail.

Two series to compute, publish and explain, which doubles the surface for confusion if the labelling
is not prominent.

The FX series inherits all the coverage and imputation caveats of the primary series, plus rate
timing.

## Alternatives considered

**TRY only.** Rejected. Ignores a substantial segment of the population and a genuine
distinction.

**One blended multi-currency index.** Rejected. Meaningless to everyone and impossible to explain.

**Convert everything to a hard currency as primary.** Rejected. TRY-earning households are the
majority and the conventional measure is the TRY one.

## Revisit trigger

The currency composition of local earnings shifts materially, or a third currency becomes
prevalent enough to warrant its own series.
