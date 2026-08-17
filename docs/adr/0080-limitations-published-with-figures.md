# ADR-0080: Limitations are published with the figures

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The sample is not random. Contributors self-select, skew urban, cluster around where they
live, and are steered by bounties toward specific cells (ADR-0020).

This is the principal threat to the validity of every figure the project publishes, and it does not
diminish with volume. More data from the same biased sample is more biased data.

A competent critic will find it. Whether they find it already disclosed or apparently concealed is
the difference between a caveat and a scandal.

## Decision

Limitations are published alongside the figures, not on request.

Disclosed in full: non-random self-selected sample; urban and contributor-location skew;
bounty-directed collection; uneven coverage by branch and category with `coverage_pct` per value;
promotional prices excluded from the index by `price_kind`; online branches excluded (ADR-0045);
unverified branches excluded (ADR-0023); imputation share per value (ADR-0077).

Stated plainly: these are figures derived from a crowdsourced corpus with a documented methodology.
They are not official statistics and are not presented as equivalent.

Post-stratification is the eventual mitigation and requires population data not currently held.

## Consequences

Credibility survives scrutiny, because the weaknesses were disclosed by the publisher
rather than discovered by a critic.

Contributor concentration becomes an operational metric with a defined response, and the response is
explicitly not automatable: it is a recruitment problem, not an engineering one
(`14-observability-analytics.md`).

Some readers will discount the figures because of the disclosure, which is the correct outcome where
the discount is warranted.

Bounties must not be so concentrated that they worsen the bias materially, which constrains how
aggressively that lever can be pulled.

## Alternatives considered

**Publish figures without limitations.** Rejected. The disclosure will happen either
way; only the framing is in question.

**Publish limitations only in a linked methodology document.** Rejected. Nobody follows the link, and
the disclosure has to travel with the number.

**Do not publish until the sample is representative.** Rejected. It may never be, and the figures are
useful with their caveats.

## Revisit trigger

Population data becomes available to support post-stratification, which would change the
mitigation rather than the disclosure.
