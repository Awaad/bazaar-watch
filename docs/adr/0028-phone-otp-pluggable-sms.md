# ADR-0028: Phone OTP authentication behind a pluggable SmsProvider

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Contributors are local residents. Email is a weaker identity signal here than a phone
number, and phone ownership raises the cost of multi-accounting, which is the main abuse vector for
a rewarded contribution system.

SMS delivery to Northern Cyprus numbers is a specific operational question, not a generic one, and
providers vary in whether they route reliably.

Every SMS costs money, which makes OTP request an abuse surface with a direct billing consequence.

## Decision

Authentication is phone OTP. `SmsProvider` is an interface with at least a fake
implementation; Preload is the initial concrete provider.

Short-lived access token, rotating refresh token.

Rate limits on OTP request per phone and per IP, enforced in Redis, tighter than on any other
endpoint.

Operators and admins additionally require a second factor and shorter sessions, because they are the
only roles that reach PII (ADR-0083).

## Consequences

Multi-accounting requires acquiring phone numbers, which is a real cost rather than
a free one.

Local test and development need no SMS credentials, since the fake provider satisfies the interface.

OTP volume is a monitored metric for both abuse and billing.

Phone numbers are personal data and are deleted outright on erasure (ADR-0071, Tier C).

A contributor who changes number needs a supported migration path, or they lose their history.

## Alternatives considered

**Email and password.** Rejected. Weaker identity, higher multi-accounting risk,
and password handling is liability without benefit here.

**Social login.** Rejected. Adds a third-party dependency and does not raise the cost of
multi-accounting meaningfully.

**Anonymous contribution.** Rejected. The trust model, reward ledger and independence rules all
require a stable identity.

## Revisit trigger

SMS delivery reliability or cost becomes a constraint, at which point the interface allows
a provider change without touching auth logic.
