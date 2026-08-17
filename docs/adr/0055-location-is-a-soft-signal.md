# ADR-0055: Location is a soft signal, never a gate

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Indoor GPS commonly degrades to 50 to 100 metres. In a shopping centre or a dense street it
cannot distinguish adjacent units, which is exactly the discrimination a validation gate would need.

Mock location is a developer-settings toggle on Android, so a determined actor defeats it trivially
while an honest contributor with a poor phone is penalised.

The cost of a false rejection is losing a contributor permanently; the cost of a false acceptance is
one flagged observation.

## Decision

Location contributes to the integrity score and never blocks a submission (ADR-0018).

A mismatch reduces reward weighting and may route to review. It never rejects and never accuses.

Declining the permission is neutral, not suspicious.

## Consequences

Honest contributors with poor GPS, indoor captures or privacy preferences are not
driven away.

The signal is genuinely weak, so it should not be weighted heavily in the integrity score, and
weighting it heavily would be a tuning error rather than a design one.

A spoofing contributor gains little, since the signal is one weak input among several structural
ones.

## Alternatives considered

**Hard gate on location match.** Rejected. Indoor drift and shopping centres would
reject real submissions at a high rate.

**Require location permission to contribute.** Rejected. Excludes privacy-conscious contributors for
a weak signal.

**Weight location heavily.** Rejected. It is not accurate enough to carry that weight.

## Revisit trigger

Positioning accuracy improves enough indoors to distinguish adjacent premises reliably.
