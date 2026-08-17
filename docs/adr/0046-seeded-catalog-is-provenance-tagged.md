# ADR-0046: Seeded catalog rows are provenance-tagged and unverified

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Typing a product catalog by hand is the cold-start burden that makes the first weeks
expensive. Scraped online catalogs supply names, brands, pack sizes, categories, barcodes and images
at essentially no cost.

Those catalogs contain the scraper's spelling errors, the seller's categorisation choices, and
products that do not exist locally.

If seeded rows are indistinguishable from operator-confirmed rows, those errors become ground truth
and are never corrected, because nothing marks them as suspect.

## Decision

`products.source` records `operator`, `scrape` or `contributor`. `verification_state` is
`unverified` until an operator confirms.

Seeded rows are usable for lexicon resolution and search immediately, because an imperfect canonical
name is far better than none.

They are visibly distinct in the console, so curation can be prioritised by whether a product is
actually being observed in receipts.

Scraping a third party has a different legal posture from receipts contributed with consent and
needs its own review before it is relied upon at scale.

## Consequences

The cold-start catalog problem largely disappears, which materially changes the first
month of operation.

Curation becomes demand-driven: products that appear in real receipts get verified first, and the
long tail can stay unverified indefinitely.

An unverified product entering a published basket would be a quality problem, so basket membership
should require verification.

The scraper's category assignments must be mapped to the curated taxonomy rather than adopted, since
the taxonomy is closed (ADR-0009).

## Alternatives considered

**Hand-build the catalog.** Rejected. Weeks of work available for free.

**Adopt scraped data as verified.** Rejected. Inherits another party's errors as fact, invisibly.

**Use scraped data only for suggestion, never as rows.** Rejected. Loses the cold-start benefit,
which is the entire point.

## Revisit trigger

Legal review of scraping, or evidence that seeded rows are degrading catalog quality faster
than curation corrects them.
