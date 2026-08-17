# ADR-0013: Pluggable ExtractionProvider with dual output and versioned runs

**Status:** Accepted
**Accepted:** 2026-08-17
**Open parameter:** Provider selection, pending the extraction bake-off. The interface, dual output, versioning and bounding-box criterion are settled.
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

Receipt extraction is the single largest external dependency. The provider landscape
moves quickly, and the best model today will not be the best model in a year.

Most document-parsing models are benchmarked on academic papers and PDF-to-markdown conversion. A
crumpled thermal receipt photographed at an angle under supermarket lighting, in Turkish, in a
truncated monospace column layout, is a different distribution, and leaderboard positions say
little about performance on it.

Cropped community review (ADR-0057) requires per-line bounding boxes. Purely generative extractors
frequently omit them.

Receipt line text is uppercase and abbreviated. `CC KOLA 1LT PET` is not a sentence, and feeding it
to an embedding model trained on natural language performs badly.

## Decision

Extraction sits behind an `ExtractionProvider` interface with at least a fake
implementation.

**Per-line bounding boxes are a hard selection criterion**, not a preference.

One pass emits both:
- `raw_text`, verbatim and immutable, feeding the lexicon key and trigram matching
- `interpreted_text`, expanded to natural language, feeding the embedding

`extraction_method` and `extraction_version` are recorded on every run, so the entire corpus can
be reprocessed when a provider improves (ADR-0082).

Selection is decided by a bake-off harness scoring line count, description accuracy, price
exactness, reconciliation rate, bounding-box quality and cost per receipt, across as many chains
and POS vendors as can be obtained.

## Consequences

Provider choice is reversible, and a better model is a configuration change plus a
backfill rather than a rewrite.

Asking for two text forms in one call costs nothing extra and removes the need for a separate
expansion step that would otherwise have to be bolted on later.

The box requirement may exclude models with better text accuracy. If so, the trade is a working
community review loop against a couple of accuracy points, and throughput compounds while accuracy
points do not.

The harness is permanent infrastructure, re-run whenever a new model lands, not throwaway spike
code.

A two-stage architecture (layout model for boxes, VLM for structuring) remains available behind the
same interface, at the cost of two versions to track.

## Alternatives considered

**Classical OCR (Tesseract and similar).** Rejected. Faded thermal print, curl, skew
and Turkish diacritics are the conditions classical OCR handles worst.

**Single hardcoded provider.** Rejected. Guarantees a rewrite when the landscape moves.

**Accept providers without bounding boxes.** Rejected as the default, because it removes the
highest-volume safe review tier. Revisited only if the accuracy gap proves large.

**Separate expansion model for `interpreted_text`.** Rejected. A second model call and a second
version to track, for something the extractor can emit for free.

## Revisit trigger

Bake-off results. Thereafter, whenever a candidate beats the incumbent on the harness by a
margin justifying a corpus backfill.
