# ADR-0050: Provisional acceptance, confirmed later

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Points are awarded on acceptance rather than submission, because rewarding submission
rewards spam.

But operator adjudication can take days. A contributor who submits and sees nothing happen will
conclude the app is broken or that their effort was ignored, and will stop. In a small community that
loss is close to permanent.

Peer review resolves within minutes rather than days, which is a different timescale entirely.

## Decision

Peer review grants `provisional` status. The ledger entry is written immediately.

Final adjudication either confirms the remainder or writes a compensating reversal (ADR-0019).

Reversals are visible to the contributor with their reason. A silent clawback is worse than no
clawback.

Observations move `pending` to `provisional` to `accepted`, with `flagged` reachable from either
intermediate state.

## Consequences

Contributors get feedback on a human timescale, which is the difference between a
retained contributor and a lost one.

Provisional observations must be excluded from published figures until confirmed, so index runs
filter on `accepted`.

A contributor can see points appear and later partly disappear, which requires clear explanation in
the app or it reads as arbitrary.

The ledger carries two entries for most accepted submissions rather than one.

## Alternatives considered

**Award only on final adjudication.** Rejected. Days of silence loses contributors.

**Award on submission.** Rejected. Rewards spam directly.

**Award provisionally with no reversal.** Rejected. Removes the consequence for bad submissions
entirely.

## Revisit trigger

Adjudication latency falls low enough that the intermediate state stops earning its
complexity.
