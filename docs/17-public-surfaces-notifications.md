# 17. Public Surfaces and Notifications

Two things that had decisions recorded against them but no document: what the public web surface
publishes, and how contributors are reminded to contribute.

## Part A: Public web

### 1. Purpose

Three audiences with different needs, served by one surface.

| Audience | Wants |
|---|---|
| Shoppers | What does this cost, where, as of when |
| Press and researchers | The published index, its methodology, its limitations |
| Search engines | Indexable pages for local product and shop queries |

The public web is a read surface. It carries no contribution flow, no operator function, and no
authenticated state beyond an optional saved location. It is a separate Next.js application from the
operator console, so an operator surface cannot leak to the public through a routing mistake
(ADR-0027).

### 2. Page types

| Page | Content |
|---|---|
| Product | Canonical name, category, current prices by branch with age, price history |
| Branch | Chain, address, map, recent observations, aggregated ordinal attributes |
| Chain | Branches, per-category index position |
| Category | Products, per-category index |
| Index | Published values by scope and series basis, with coverage and imputation share |
| Methodology | The full content of `08-index-methodology.md`, published |

Every URL uses slugs. Internal UUIDs never appear, both because they are not a stable public
contract and because time-ordered identifiers on a public page let an observer estimate submission
volume, which is commercially sensitive while coverage is thin (ADR-0003).

### 3. Staleness is never hidden

**No page displays a price without its age.** Not as a tooltip, not on hover, not behind a
disclosure. Age sits next to the number.

This is not a nicety. Under high inflation a two-week-old price is misleading, and a surface that
hides that is lying during exactly the periods when accuracy matters most (ADR-0029).

Prices older than the display staleness threshold are shown greyed with an explicit "last seen"
framing rather than as a current price.

### 4. What the public surface does not expose

| Withheld | Reason |
|---|---|
| Receipt-level grouping | It is a basket, and a basket is re-identifying in a small market (ADR-0085) |
| Contributor identity on any observation | Same reason, plus ADR-0051 |
| Internal identifiers | Volume inference, and they are not a stable contract |
| Trust scores, integrity signals, honeypot status | Publishing them is publishing the evasion guide (ADR-0018) |
| Provisional or flagged observations | Only `accepted` observations are published |
| Index values below the coverage floor | Suppressed rather than published thin (ADR-0029) |

### 5. Publication of figures

Every published index value carries its methodology version, taxonomy version, coverage percentage,
imputation share and median staleness. A value cannot render without them.

Both currency series are shown with their labels, neither presented as the real one (ADR-0078).

The limitations section is published with the figures, not linked from them. Nobody follows the link,
and the disclosure has to travel with the number (ADR-0080).

### 6. SEO

Server-rendered. Local search intent is the acquisition channel: someone searching for a product name
plus a town should reach a product or branch page.

Structured data markup for products and local businesses. Turkish as the default locale with
`hreflang` alternates for EN, RU and DE. Category and methodology pages are the stable content;
price pages change constantly and are marked accordingly.

Attribution for Overture Places appears in the site footer as the licence requires (ADR-0022).

## Part B: Notifications

### 7. What exists

Background geofenced reminders are deferred, because they are the only feature requiring
continuous background location, and that permission carries app store friction and a high denial
rate for a benefit that is assumed rather than measured (ADR-0056).

What ships instead:

| Trigger | Purpose |
|---|---|
| Time-based, on a contributor's usual shopping days | The receipt still exists and intent is highest shortly after shopping |
| App open | Pending review tasks, unsynced queue items |
| Review outcome | A submission moved to accepted, or a reversal with its reason |
| Bounty in a contributor's area | Cold cell nearby, tied to the coverage sweeps (ADR-0020) |

Reversals are always notified with their reason. A silent clawback is worse than no clawback
(ADR-0050).

### 8. Storage and erasure

`push_tokens` holds platform, token, locale and enabled state, unique on `(platform, token)` because
a device can be reassigned between accounts.

Tokens are **Tier C** under the erasure model: deleted outright, not shredded and not severed
(ADR-0071).

Notification content is localised server-side from ICU keys using `push_tokens.locale`, which may
differ from the account locale if a contributor uses more than one device.

### 9. What is never in a notification

Basket contents, product names from another contributor's submission, or anything that would carry
receipt-level information to a device. Notifications are a side door into the same data the public
surface withholds, and they are subject to the same rules (ADR-0085).

Notification analytics record delivery and open events, never payload composition.

### 10. Frequency

Contributors control notification categories independently, and every category can be disabled
without affecting contribution or reward.

A frequency ceiling from `tuning.json` applies regardless of category, so a burst of bounty
generation cannot produce a burst of notifications (ADR-0021). Notification fatigue costs a
contributor permanently, and in a community this small that loss is close to irreversible.
