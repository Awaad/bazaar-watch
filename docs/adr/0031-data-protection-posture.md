# ADR-0031: Data protection: minimise at ingest, sever on erasure

**Status:** Accepted
**Accepted:** 2026-08-17
**Open parameter:** Regulatory detail on retention, notification timelines and assessment obligations, pending local legal review. The minimisation and erasure posture is settled.
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Receipt images carry card digits, loyalty numbers, occasionally staff or customer names,
and the complete basket of one person at one place and time. Baskets support inferences about
health, religion, pregnancy and alcohol use, and a sequence of them is a movement pattern.

Contributors include EU data subjects. Northern Cyprus has its own regime. The precise obligations
require local legal review that has not happened.

Most of the corpus, meaning observations, catalog, branches and index values, is not personal data
once unlinked.

## Decision

Minimise at ingest rather than remediate later:

- Images are re-encoded on ingest, stripping EXIF including embedded GPS (ADR-0068).
- Capture location is consumed and discarded; only a derived match flag persists (ADR-0054).
- Review tiers are designed so T1 and T2 expose no PII by construction (ADR-0057).

Erasure severs identity rather than destroying facts, with three tiers (ADR-0071).

Consent is explicit and separable at signup: account, contribution and publication, optional
location, optional review participation.

Detail on retention windows, notification timelines and assessment obligations is blocked on legal
review and does not gate T1 or T2 contribution.

## Consequences

The minimisation decisions hold under any plausible regime, so the legal answer
changes retention and T3 rather than the architecture.

Declining location does not block contribution; it removes one soft integrity signal.

An unanswered legal question no longer blocks the product, because review tiering removed the
dependency.

Consent granularity means the signup flow is longer than a single checkbox, which is the correct
trade.

## Alternatives considered

**Blanket consent at signup.** Rejected. Not meaningful consent, and it collapses
under scrutiny.

**Store everything and remediate on request.** Rejected. Remediation cannot reach immutable
replicas, which is what forced crypto shredding (ADR-0086).

**Wait for legal review before building anything.** Rejected. The minimisation decisions are correct
under any regime and blocking on them would stall indefinitely.

## Revisit trigger

Local legal review completes, or a contributor exercises a right the current design does
not cleanly support.
