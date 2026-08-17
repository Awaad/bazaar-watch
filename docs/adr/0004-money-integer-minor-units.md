# ADR-0004: Money as integer minor units with explicit currency

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Prices are the primary data of the system. TRY has kuruş as a minor unit. Northern
Cyprus also transacts in GBP, EUR and USD, and contributors may capture prices in any of them.

Floating point arithmetic on currency accumulates error and produces comparisons that are wrong
in ways that never raise an exception.

Converting a price at capture time destroys the original fact and bakes in a rate that cannot
later be audited or corrected.

## Decision

All monetary values are stored as `*_minor BIGINT` alongside `currency CHAR(3)`.
Never float, never `NUMERIC` used as a money type.

Observations store the **observed currency** and are never converted on write.

Conversion happens at read time using rates recorded in `fx_rates` with an `as_of` date. Any
response that converts carries the rate and its date, so the conversion is reproducible.

Money crosses the API as an object, `{ "amount_minor": 4590, "currency": "TRY" }`, never as a
bare number and never pre-formatted.

A `Money` type in `core` is the only sanctioned representation, and CI fails on float arithmetic
against price fields.

## Consequences

No rounding drift, and equality comparisons behave.

Historical prices remain auditable in the currency in which they were observed, and a corrected
FX rate changes derived views without touching facts.

Every read path that converts must join `fx_rates`, which is slightly more work than storing a
converted column.

Formatting happens at the client edge, which means the server never needs to know a viewer's
locale (see `11-i18n-localization.md`).

## Alternatives considered

**Float or double.** Rejected outright.

**`NUMERIC(12,2)`.** Rejected. Correct arithmetically, but it invites accidental float conversion
in application code and does not prevent the mistake at the type level.

**Convert to TRY at capture.** Rejected. Destroys the original fact and makes a later rate
correction impossible.

## Revisit trigger

Never.
