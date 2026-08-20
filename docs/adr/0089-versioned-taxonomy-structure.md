# ADR-0089: Taxonomy structure is versioned, category identity is not

**Status:** Accepted
**Accepted:** 2026-08-20
**Date:** 2026-08-20
**Supersedes:** none
**Superseded by:** none

## Context

`categories.taxonomy_version` was an integer column on a single mutable tree,
and `index_runs` and `index_values` both carried the same integer. No table
defined it, so a published figure named a version that could not be looked up.

The obvious repair is a `taxonomy_versions` table and a foreign key. That fixes
the dangling reference and does not fix the harder problem.

ADR-0079 rule 3 requires a methodology change to run both series in parallel for
three cycles, published side by side, and its consequences section names a
taxonomy restructure as expensive under exactly that rule. Parallel running two
taxonomies means computing **new** index values under the **old** tree, for
products observed during those cycles, including products created after the
restructure. One mutable tree cannot do that: the old shape is gone the moment
the new one is saved.

So a version column buys labelling, which tells a reader that two figures are
not comparable. Parallel running needs both shapes live at once.

Versioning the whole category row was considered and rejected. A category slug
is a URL, and duplicating rows per version either makes slugs unique per version,
which moves a category on the web every time the tree is reorganised, or keeps
them globally unique, which the duplication makes impossible.

## Decision

Identity and shape are separate tables.

`categories` holds identity: the id a product points at, a globally unique slug,
and the translated names. It is stable across restructures and has no version.

`category_structure` holds shape, keyed by `(category_id, taxonomy_version)`:
parent, materialised path, sort order. Two versions of the tree coexist as two
sets of rows.

`parent_id` is the source of truth and carries a composite foreign key into
`category_structure`, so a parent is necessarily a node in the same version.
`path` is derived, maintained by a trigger, and never written by the
application, for the same reason `updated_at` is: a value the application
maintains is wrong the moment anything writes outside the ORM.

`categories` has no status column. Membership in the active version's structure
is what makes a node live, and a status beside it is a second way to say the
same thing that can disagree with the first.

A restructure that merges two nodes genuinely changes identity, and the retired
node records `superseded_by_id` so its history has somewhere to go.

## Consequences

Two taxonomies can be live at once, so ADR-0079 rule 3 is satisfiable rather
than merely stated.

A category keeps its URL across restructures, which is what a stable slug on the
identity table buys.

`products.category_id` points at identity and does not move when the tree does.
That is the main reason this shape is cheaper than versioning whole rows.

Every query about the shape of the tree must name a taxonomy version. There is
no such thing as "the parent of this category" without one, which is more
verbose and is also true.

The merge case is the weak spot. `superseded_by_id` records where a retired node
went, but recomputing an old series across a merge still needs the old
product-to-category assignment, which this decision does not provide. If merges
turn out to be common, that assignment needs versioning too.

## Alternatives considered

**One mutable tree, version as provenance.** Rejected: fails ADR-0079 rule 3,
which is an Accepted decision and not one this record is entitled to weaken.

**Versioned category rows.** Rejected: forces the slug to be either unique per
version, which moves URLs on every restructure, or globally unique, which
duplication makes impossible. It also requires a versioned product-to-category
mapping table for every restructure rather than only for merges.

**Reconstruct the old tree from `audit_log`.** Rejected. Recomputing a published
series from an audit trail makes the correctness of a figure depend on the
completeness of a log written for a different purpose.

## Revisit trigger

The first restructure that merges or splits nodes, which is where a versioned
product-to-category assignment becomes necessary rather than theoretical.
