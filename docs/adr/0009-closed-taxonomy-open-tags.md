# ADR-0009: Closed curated versioned taxonomy; open facet tags

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The category tree carries two jobs. It classifies products for browsing and for
per-category index computation, and because the catalog is Turkish with no supply side to
localise it, a fully translated tree is what makes an untranslated catalog reachable in four
languages.

If contributors or a model could create categories, the tree degenerates within weeks and every
basket weight built on it becomes meaningless.

Restructuring changes what a category index means, even when no formula changed.

## Decision

The taxonomy is closed, curated, hierarchical and versioned. Operators alone create
nodes.

Nodes must be retrieval-shaped, not merely taxonomically correct, and every node requires
complete `name_i18n` coverage before a version can be marked active. Roughly 150 nodes across
four locales.

The taxonomy maps to COICOP division 01, which is most of what makes published figures
comparable to official statistics (ADR-0075).

Facets are a separate, open set: `halal`, `organic`, `imported`, `refrigerated`,
`private_label`.

A restructure bumps `taxonomy_version`, and every index run records the version that produced
it. A restructure counts as a methodology change (ADR-0079).

## Consequences

Category translation is bounded, one-time work with a clear completion criterion,
enforced by the `taxonomy-i18n-complete` CI gate.

Browse and filter work in every locale even where product names exist only in Turkish.

Operators are a bottleneck for new categories, which is intended.

Published category indices are comparable across time only within a taxonomy version, and the
version is published alongside every value.

## Alternatives considered

**Open taxonomy.** Rejected. Degenerates, and takes the index weights with it.

**Flat categories.** Rejected. No subtree aggregation, which per-category indices require.

**Tags only, no hierarchy.** Rejected. Browse needs hierarchy and index aggregation needs
subtrees.

**Skip COICOP mapping.** Rejected. It costs little at design time and is most of the argument for
taking the figures seriously.

## Revisit trigger

Category creation demand consistently outstrips operator capacity, or COICOP alignment
proves to distort local shopping categories badly enough to hurt usability.
