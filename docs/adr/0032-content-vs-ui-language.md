# ADR-0032: Content language and interface language are separate decisions

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

These are constantly conflated and have different natures. Interface language is a choice.
Content language is a physical constraint: receipts, fascias and packaging are Turkish.

A retailer solves this by having sellers submit localised titles. There is no supply side here, so
the catalog cannot be localised by the same mechanism.

Different demographics want disjoint product sets. A German looking for Quark and a Russian looking
for tvorog and an Arab looking for tahini need three different product sets, each requiring its own
coverage, which makes translation-as-strategy unbounded.

## Decision

Interface: TR, EN, RU, DE, with Arabic layout-ready (ADR-0026).

Content: Turkish. Product canonical names, receipt raw text and brand names stay as they are.

The bridge is dense cross-lingual retrieval (ADR-0024), not translation. Aliases are an override
layer for what a web-trained model cannot know, meaning local brands and regional names
(ADR-0037).

The taxonomy is fully translated, because browse and filter need it and search does not replace
navigation.

## Consequences

Search works across four languages against a Turkish catalog without a translation
project.

Users see Turkish product names in a Russian interface, which is correct and needs explaining in the
UI rather than hiding.

The Turkish fold governs content matching and never the interface, which is why ADR-0025 exists
separately.

The alias backlog is demand-ranked from query logs rather than guessed (ADR-0039).

## Alternatives considered

**Translate the catalog.** Rejected. Unbounded across disjoint demographic product
sets, and it grows with the catalog.

**Turkish-only interface.** Rejected. The largest growth demographic does not read Turkish.

**Machine-translate product names on the fly.** Rejected. Produces confident nonsense on local brand
names and pack descriptors.

## Revisit trigger

Never. This separation is structural.
