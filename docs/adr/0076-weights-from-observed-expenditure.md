# ADR-0076: Weights derived from observed expenditure

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Higher-level index aggregation needs expenditure weights. Statistical offices obtain them
from an annual household expenditure survey, which is typically their most expensive input and is
already a year stale when used.

Receipts carry quantities as well as prices, which makes the corpus expenditure data rather than
merely price data.

This is a genuine advantage over conventional practice and over every other crowdsourced price
project, and it should be used rather than ignored in favour of borrowed weights.

## Decision

Weights derive from observed expenditure in the corpus and refresh continuously.

`basket_items.weight_source` records provenance:

- `observed_expenditure`, derived from the corpus. Preferred.
- `coicop_reference`, published reference weights, used where corpus coverage is too thin.
- `manual`, operator override, requiring a recorded reason.

Weight refresh is a chained basket update (ADR-0075), not a break in the series.

## Consequences

Weights reflect what people here actually buy, continuously, rather than a national
survey from last year.

Weight quality depends on corpus coverage and inherits its sample bias, which is disclosed
(ADR-0080). Contributor baskets are not a random sample of household consumption.

Reference weights provide a fallback where coverage is thin, and the mix is visible per basket item
rather than hidden.

Continuous refresh means weights must be pinned per index run, or a rerun produces a different
figure.

## Alternatives considered

**Published national reference weights only.** Rejected. Discards the corpus's main
methodological advantage.

**Equal weights.** Rejected. Treats salt and milk as equally important, which no consumer would
recognise.

**Operator-assigned weights.** Rejected as the primary source. Retained as an override with a
recorded reason.

## Revisit trigger

Sample bias is measured to be severe enough that observed weights are less representative
than reference weights.
