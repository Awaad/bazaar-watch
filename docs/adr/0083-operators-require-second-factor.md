# ADR-0083: Operators require a second factor

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Operators and admins are the only roles that reach receipt originals, and therefore the only
roles that see PII.

They also hold the decisions the corpus depends on: lexicon resolution, product merges, branch
verification and adjudication. A compromised operator account can corrupt the dataset as well as
expose data.

Treating them as ordinary contributors with a wider role check would leave the most sensitive access
path protected by exactly the same phone OTP as the least sensitive one.

## Decision

Operators and admins require a second factor beyond phone OTP, and shorter session
lifetimes.

Every operator action writes to `audit_log` with before and after state.

`/v1/ops/*` is a separate endpoint group rather than a role check on shared routes, carrying different
rate limits, different audit logging and different response shapes. The separation makes an
authorization mistake structurally harder.

Authorization is enforced in the service layer, never in a route decorator alone, because the same
operation is reachable from more than one route.

## Consequences

The most sensitive path is the best protected, which inverts the common default.

Operator friction increases, which is acceptable for a small number of trusted users doing sustained
sessions rather than quick interactions.

`audit_log` becomes the record that answers who saw what before an incident, and it outlives ordinary
logs.

An erased operator's `actor_id` is tombstoned like any other, but the record that a decision was made
survives (ADR-0084).

## Alternatives considered

**Same auth for all roles.** Rejected. The most sensitive path would be the least
protected.

**IP allowlisting instead of a second factor.** Rejected. Brittle for a mobile operator and it does
not protect against a compromised device.

**Operator access only from a separate network.** Rejected as impractical for a small distributed
team.

## Revisit trigger

Operator count grows enough to warrant a more granular permission model than four roles.
