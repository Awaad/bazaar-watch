# ADR-0026: Four launch locales with Arabic layout-ready from the first commit

**Status:** Accepted
**Accepted:** 2026-08-17
**Date:** 2026-08-17
**Supersedes:** none
**Superseded by:** none

## Context

The user base is not primarily Turkish-reading. Expatriates and digital nomads are a target
demographic, and Russian and German speaking residents are a substantial population in Northern
Cyprus.

Retrofitting right-to-left layout across a built interface is expensive. Building with logical
properties from the start costs nothing.

The operator console is a different case: moderators work in Turkish or English, and dense
bidirectional review tables are the hardest RTL case there is.

## Decision

Interface locales at launch: `tr`, `en`, `ru`, `de`. Arabic is layout-ready and
untranslated.

ICU MessageFormat throughout, with keys served from the server so a wording fix does not require an
app release.

Logical properties only: `margin-inline`, `padding-inline`, `inset-inline`, `text-align: start`.
Never `left` or `right`. Direction-encoding icons mirrored via `:dir(rtl)`.

The operator console is LTR-only by decision, recorded as a scope boundary rather than left as an
oversight.

CI fails on literal strings in UI code and on locale files missing keys present in another.

## Consequences

Arabic ships as a supported layout with English strings, and translation becomes a
content task rather than an engineering one whenever demand justifies it.

Server-served keys mean copy changes do not wait on app store review, which matters because app
review latency is the one thing that cannot be engineered around.

Russian plural rules have four categories, so hardcoded singular and plural branches are wrong
everywhere and ICU is not optional.

Four locales multiply the translation cost of every new string, which is a real ongoing tax.

## Alternatives considered

**Turkish and English only, add more later.** Rejected. RTL and pluralisation
retrofits are the expensive part, and both are cheap now.

**Arabic fully translated at launch.** Rejected. No demand signal, and the catalog is Turkish
regardless.

**Client-bundled locale files only.** Rejected. Every copy fix would require an app release.

**RTL support for the console too.** Rejected on cost against a known LTR-reading audience.

## Revisit trigger

Measured Arabic-locale usage justifies translation, or a moderator cohort emerges that
needs RTL.
