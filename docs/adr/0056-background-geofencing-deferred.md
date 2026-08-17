# ADR-0056: Background geofenced reminders are deferred

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A reminder triggered on leaving a supermarket would plausibly lift contribution rates
substantially, because the moment of highest intent is immediately after shopping.

It is also the only feature requiring continuous background location. Apple scrutinises Always
permission requests, Google Play requires a background location declaration with review, and users
deny the permission at high rates.

The cost is therefore paid at app review and at the permission prompt, and if the user declines, the
cost is paid for nothing.

## Decision

Background geofenced reminders are deferred.

Foreground and time-based nudges are used instead: a prompt on app open, and scheduled reminders on a
contributor's usual shopping days.

Revisited once retention data shows the geofenced version would materially outperform, which makes
the app store cost worth paying.

## Consequences

The permission surface stays narrow, which helps both approval and grant rates.

The reminder is less well-timed, which likely costs some contributions.

If revisited, it is an additive change: the derived-location design (ADR-0054) does not need
unwinding, only extending, and it would need its own consent.

## Alternatives considered

**Ship geofencing at launch.** Rejected. Pays the highest permission cost before any
evidence it is worth it.

**No reminders at all.** Rejected. The post-shopping moment is when a receipt still exists and intent
is highest.

**Significant-location-change APIs.** Deferred with the same reasoning; lower cost than full
geofencing but still a background permission.

## Revisit trigger

Measured contribution rates against time-based reminders show a gap large enough to justify
the permission cost.
