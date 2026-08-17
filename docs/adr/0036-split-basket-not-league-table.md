# ADR-0036: The split basket, not a league table, is the consumer surface

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The question a shopper actually has is not "which shop is cheapest" but "given my list,
and how far I am willing to go, where do I buy what".

A store league table answers a question nobody asks and is only actionable if the ordering is
stable and unconditional. It is neither (ADR-0034).

This is arithmetic over the price table, not a recommendation problem. It needs no model, and a
model would be worse because it could not explain itself.

## Decision

Given a list, a store-count budget and a reachability constraint, compute where to buy
what.

Deterministic optimisation over current observations, with an explicit substitution policy
(ADR-0041) and an explicit missing-item policy.

Every recommendation is explainable to a user who asks why, because it is a sum with stated inputs.

Prices shown carry their observation age. There is no surface that displays a price without its
staleness.

## Consequences

The consumer feature is explainable, debuggable and cheap to compute.

It depends entirely on coverage and freshness for the user's specific list and reachable set, so a
thin corpus produces a thin answer and must say so rather than guess.

Missing-item policy is a product decision with visible consequences, not an implementation detail.

Promotional prices are included here, unlike in the index, because a promotion is exactly what a
shopper wants to know about.

## Alternatives considered

**Cheapest-store ranking.** Rejected. Not actionable under conditional ordering.

**Machine-learned recommendation.** Rejected. No behavioural data, no need for one, and it could not
explain a recommendation the user disputes.

**Show all prices and let the user decide.** Rejected as an abdication; the aggregation is the
value.

## Revisit trigger

Usage shows people want a single store answer rather than a split, which would be a
finding about willingness to visit multiple shops.
