# ADR-0011: The model suggests, the human decides

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Three decisions determine data quality: which canonical product a receipt string maps
to, whether two products are the same, and whether a branch candidate is real.

All three are automatable with plausible accuracy. All three fail silently when wrong, and all
three propagate: a wrong lexicon entry misattributes every past and future observation carrying
that key.

Suggestion quality will improve over the project's life. The cost of a wrong automated decision
does not.

## Decision

No automated process writes a lexicon entry, a product merge, or a branch
verification.

Suggestion ranks candidates only. It uses hybrid retrieval over the shared embedding index:
trigram over `lexical_text` for brand and near-literal matches, dense vectors over
`semantic_text` for everything else, fused by reciprocal rank fusion (ADR-0024, ADR-0040).

Every candidate list includes an explicit "none of these" that escalates to an operator.

`chain_lexicon.decided_by` and `branches.verified_by` are `NOT NULL`, so the invariant is
structural rather than procedural.

T1 community review counts as a human decision, recorded as `decided_via = 'review_t1'` and
subject to quorum and independence rules (ADR-0047, ADR-0048).

## Consequences

Throughput is bounded by human attention, which is why T1 review exists and why
suggestion quality matters even though suggestion never decides.

Every approved decision is a labelled training example, so the suggestion layer improves from its
own supervision without ever being trusted to act.

Escalation paths must exist everywhere, since "none of these" is a normal outcome rather than an
error.

The system cannot bootstrap unattended. Accepted deliberately.

## Alternatives considered

**Auto-accept above a confidence threshold.** Rejected. Generative confidence is
uncorrelated with correctness on exactly the hard cases, and a wrong mapping propagates
retroactively.

**Auto-accept then human audit.** Rejected. Auditing a decision already applied to a thousand
observations is more expensive than making it once.

**Fully manual with no suggestion.** Rejected. Suggestion does not compromise the invariant and
is the difference between a viable and an unviable review rate.

## Revisit trigger

Measured suggestion top-1 accuracy is high enough, over a large enough adjudicated
sample, to justify supervised bulk approval of a ranked batch. Even then the human approves the
batch; the model still does not write.
