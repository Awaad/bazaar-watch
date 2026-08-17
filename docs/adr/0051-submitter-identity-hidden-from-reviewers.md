# ADR-0051: Submitter identity is never shown to reviewers

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

In a market of this size, identifying details compose quickly. Someone who shops at a
particular branch on Tuesday evenings can be one person, and a reviewer who recognises a name can
infer a great deal from what they are reviewing.

Reviewers see receipt content, which is basket data carrying inferences about health, religion,
pregnancy and alcohol use.

Naming the submitter also creates a social dynamic where review outcomes track personal relationships
rather than evidence.

## Decision

Submitter identity is never shown to a reviewer, at any tier.

Leaderboards show display names but never link an entry to a specific submission, which would defeat
this by a different route.

Combined with the tiered review design (ADR-0057), a T1 reviewer sees a text string and a T2 reviewer
sees one cropped line, neither of which identifies anyone.

## Consequences

Review outcomes track evidence rather than relationships.

Re-identification through the review surface is structurally difficult rather than merely
discouraged.

Reviewers cannot flag a specific contributor as suspicious, which is the intended trade: pattern
detection belongs to the integrity signals, not to reviewer intuition.

Leaderboard design is constrained, since submission-level attribution is off the table.

## Alternatives considered

**Show submitter identity.** Rejected. Re-identification risk and social bias in
outcomes.

**Show a stable pseudonym.** Rejected. A pseudonym links a person's submissions to each other, which
is the same profile-building problem addressed in ADR-0084.

**Show identity only to high-trust reviewers.** Rejected. Adds a privilege tier for no benefit that
integrity signals do not already provide.

## Revisit trigger

Never.
