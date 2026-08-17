# ADR-0060: Closed questions, not open transcription

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

A review task can ask "what does this say" or it can ask "does this say 45.90 or 46.90".

Open transcription produces high variance in answers: whitespace, casing, abbreviation choices and
typos all differ between reviewers who are all effectively correct. Scoring agreement across that
variance is hard and unreliable.

Closed questions are also much faster to answer, which matters because throughput is the point.

## Decision

Review questions are closed form with explicit options.

For T2, the options are the extracted value and the most plausible alternatives, typically derived
from the reconciliation residual analysis (ADR-0058).

For T1, the options are ranked candidates from hybrid retrieval, plus an explicit "none of these"
that escalates to an operator (ADR-0011).

`review_tasks.question` holds the prompt and options as structured data, so the same task can render
in any locale.

## Consequences

Answers are directly comparable, so weighted agreement and quorum are simple to
compute.

Tasks are fast enough to be done in spare moments, which suits mobile contribution.

Question construction requires the system to already have a hypothesis, which is fine for T2 where
extraction produced one, and requires the suggestion layer for T1.

A correct answer outside the offered options is only reachable through "none of these", so that
escape hatch must always be present and must not be penalised.

## Alternatives considered

**Free-text transcription.** Rejected. High variance, hard to score, slow to answer.

**Binary confirm or reject.** Rejected. Loses the information about what the correct value actually
is.

**Open transcription with fuzzy agreement scoring.** Rejected. Adds a matching problem on top of the
one being solved.

## Revisit trigger

A task type emerges where the answer space cannot be enumerated, which would need operator
handling rather than a different question format.
