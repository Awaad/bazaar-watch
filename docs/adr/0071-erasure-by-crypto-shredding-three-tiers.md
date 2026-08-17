# ADR-0071: Erasure by crypto shredding, scoped to three tiers

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

"Nothing is deleted" (ADR-0006) is a governing principle of the data model. Erasure is a
legal right. Both cannot be applied literally to the same data.

Most of the corpus is not personal data. A shelf price is a fact about a shop, and once unlinked from
a contributor it says nothing about a person. Encrypting it per contributor would destroy the
aggregate queryability that is the entire product.

Receipt images are different. They are one person's complete basket at one place and time, carrying
card digits, loyalty numbers and inferences about health, religion, pregnancy and alcohol use.

Ordinary deletion cannot reach object-locked replicas, which exist by mandate (ADR-0069).

## Decision

Three tiers.

**Tier A**, originals, crops and raw PII fields: envelope encrypted under a per-subject key
encrypting key. Erasure destroys the KEK, rendering every object under it permanently unreadable
including in immutable replicas and versioned objects.

**Tier B**, observations, receipt lines and ledger entries: severed to the shared tombstone
(ADR-0084) and retained in plaintext. A shelf price is not personal data once unlinked.

**Tier C**, phone, credentials, sessions and push tokens: deleted outright.

`users.erased_at` is set and identifying fields are nulled, enforced by check constraint.

## Consequences

The principle and the legal right coexist without either being compromised.

Aggregate figures remain correct after erasure, because the facts survive.

Key management becomes a real operational responsibility, with a specific and easily-broken
constraint (ADR-0072).

An erased contributor's media cannot be reprocessed, so their observations are frozen at their last
extraction version.

The extraction fine-tuning corpus shrinks with each erasure (ADR-0073).

## Alternatives considered

**Delete everything belonging to the contributor.** Rejected. Destroys facts about
shops that are not personal data, and cannot reach locked replicas anyway.

**Encrypt the whole corpus per contributor.** Rejected. Aggregate queries become impossible, which
removes the product.

**Refuse erasure, citing immutability.** Rejected. Not lawful, and not defensible.

**Anonymise images by blurring.** Rejected. Depends on detection being perfect across every layout,
and a miss is invisible.

## Revisit trigger

Legal review returns guidance that Tier B severing is insufficient, which would force a
reconsideration of what counts as personal data here.
