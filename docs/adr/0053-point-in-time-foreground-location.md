# ADR-0053: Point-in-time foreground location only

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Location has three plausible uses here and they carry wildly different costs.

Validating that a contributor was at the claimed branch needs a single fix at capture. Targeting peer
review to people familiar with a branch can be derived from prior contributions, which are already
recorded. Geofenced reminders after shopping need continuous background location.

Continuous background location is among the highest-risk processing categories under any data
protection regime, and both major app stores scrutinise the permission.

## Decision

A single foreground fix at the moment of capture. No history, no background tracking, no
trace.

Peer review targeting uses prior contributions at that branch, already present in `submissions`.
Deriving it from stored location history would be strictly more invasive for the same result.

Background geofenced reminders are deferred (ADR-0056).

Declining the permission does not block contribution; it removes one soft integrity signal.

## Consequences

The permission request is narrow and explicable, which improves the grant rate as
well as the risk posture.

No location history exists to leak, to subpoena, or to erase.

Reminder features must use foreground or time-based triggers until the deferral is revisited.

The validation signal is available only when the app is open at capture, which is the normal case.

## Alternatives considered

**Continuous background location.** Rejected. Highest-risk processing category, app
store friction, likely user denial, for one deferred feature.

**Location history for review targeting.** Rejected. More invasive than the derived alternative, for
the same outcome.

**No location at all.** Rejected. The capture-moment fix is a genuinely useful soft signal at near
zero cost.

## Revisit trigger

Retention data shows geofenced reminders would materially change contribution rates, at
which point ADR-0056 is revisited rather than this one.
