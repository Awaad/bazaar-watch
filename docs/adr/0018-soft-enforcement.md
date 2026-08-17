# ADR-0018: Soft enforcement: reduce reward and route to review, never accuse

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Costs are asymmetric. A false accusation loses a contributor permanently, in a small
community where contributors are the scarcest resource and where word travels. A false acceptance
costs one flagged observation excluded from published figures.

Several signals are weak by nature. Indoor GPS drifts 50 to 100 metres. Clients legitimately strip
EXIF. Genuine prices are wildly dispersed.

## Decision

A low integrity score reduces reward and routes to review. It never hard-blocks a
submission and never accuses a contributor.

Missing EXIF is neutral, since clients strip it and the server re-encodes anyway (ADR-0068).

Signals combine into a score. No single signal is a threshold that rejects.

Rate anomalies are signals, not rules: a contributor suddenly submitting forty receipts in a week
may be farming or may have just discovered the app.

Internal signal detail, trust scores and honeypot status are never serialised to a contributor
client.

## Consequences

Honest contributors with poor phones, bad lighting or weak GPS are not driven away.

Some bad data enters `pending` and is caught at adjudication rather than at the door, which is the
intended trade.

Every rejection is a human decision recorded in `audit_log`, which means a contributor dispute has
an answer.

Reward reduction must be explained to the contributor, since a silent reduction is as damaging as an
accusation.

## Alternatives considered

**Hard blocking on threshold.** Rejected. Weak signals plus a hard gate produces
false rejections of exactly the contributors worth keeping.

**Full transparency of integrity scoring.** Rejected. Publishing the scoring function is publishing
the evasion guide.

**Silent shadow-banning.** Rejected. Ethically poor and destroys trust when discovered, which it
always is.

## Revisit trigger

Deliberate abuse reaches a volume where triage cost exceeds the cost of some false
rejections.
