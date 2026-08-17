# ADR-0047: Peer review verifies extraction, not price

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Community review is the obvious answer to a throughput bottleneck, but it is easy to point
at the wrong target.

A reviewer was not standing at that shelf at that moment. They cannot adjudicate whether a price was
correct, and asking them to would produce confident answers with no basis.

What they can verify is what the source says: whether a receipt is real and legible, whether the
store matches, whether an extracted line matches the image, and which canonical product a receipt
string denotes.

That last one is the lexicon gap queue, which is the actual bottleneck of the entire system.

## Decision

Peer review verifies **extraction**, never price.

Reviewers answer questions about what a source states, not about whether the world matched it.

The highest-volume tier is lexicon mapping, which drains the queue that would otherwise be one
person at a keyboard.

Price correctness is established by corroboration across independent observations at the same
branch, not by review.

## Consequences

Review targets the bottleneck rather than a plausible-sounding but unanswerable
question.

Community contribution scales normalization throughput, which is the constraint on everything
downstream.

Fabricated prices on well-formed receipts remain undetectable by review, which is why structural
integrity signals carry that load (ADR-0017) and why coverage matters for corroboration.

Review UX can be simple, because the questions are closed and objective.

## Alternatives considered

**Review prices for plausibility.** Rejected. The reviewer has no basis, and in a
high-dispersion market plausibility judgements would systematically reject real data (ADR-0033).

**Operator-only review.** Rejected. It is the bottleneck the system needs to escape.

**No review, trust extraction.** Rejected. Generative extraction hallucinates confidently
(ADR-0014).

## Revisit trigger

Extraction accuracy becomes high enough that verification volume no longer justifies a
community tier, which would be a good problem.
