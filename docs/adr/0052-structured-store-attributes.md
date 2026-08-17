# ADR-0052: Structured store attributes only, never free text

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Price is not the whole shopping decision. Produce freshness, stock breadth and queue length
are real differentiators, and the founding observation of this project includes the fact that a
nearby shop may have better fresh goods.

Free-text store reviews would capture this. They would also create a moderation burden, and
publishing "this store cheats you" carries defamation exposure in a small market where those same
stores may later be partners or advertisers.

Subjective quality ratings must also never touch the price index, or the index becomes indefensible.

## Decision

Fixed ordinal dimensions only: produce freshness, stock breadth, queue length. No free
text.

Recency-weighted, because freshness last March says nothing about today.

Suppressed below a minimum sample count rather than displayed thin.

Rigorously excluded from the price index (ADR-0029). A subjective rating contaminating a published
inflation figure would destroy its credibility.

Free-text store reviews are declined.

## Consequences

The moderation burden is bounded, since there is no prose to moderate.

Ratings aggregate into something comparable rather than into a sentiment blob.

Defamation exposure is minimal, because the platform publishes distributions of ordinal ratings
rather than accusations.

Some genuine information is lost. A shop with a specific recurring problem cannot be described,
only rated.

## Alternatives considered

**Free-text reviews.** Rejected. Moderation burden and defamation exposure in a small
market.

**No store attributes at all.** Rejected. Discards a real differentiator that users care about.

**Free text with moderation.** Rejected. The moderation cost is unbounded and falls on one person.

## Revisit trigger

Structured dimensions prove insufficient to capture what users actually want to
communicate, evidenced by usage rather than assumption.
