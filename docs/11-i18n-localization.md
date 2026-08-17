# 11. Localization

Two decisions that are constantly conflated and must stay separate. (ADR-0032)

**Interface language** is a choice. TR, EN, RU, DE at launch, Arabic structurally supported.

**Content language** is a physical constraint. Receipts, fascias and packaging are Turkish, and
unlike a retailer we have no supply side to localise the catalog. Cross-language reach is solved
by retrieval, not translation.

## 1. Interface

| Locale | Status |
|---|---|
| `tr` | Launch |
| `en` | Launch |
| `ru` | Launch |
| `de` | Launch |
| `ar` | Layout-ready, untranslated |

ICU MessageFormat throughout, keys served from the server so a wording fix does not require an
app release. CI fails on literal strings in UI code and on locale files missing keys present in
another. (ADR-0026)

The operator console is LTR-only by decision. Moderators work in Turkish or English, and dense
bidirectional review tables are the hardest RTL case there is. Stated as a scope boundary rather
than left as an oversight.

## 2. Arabic without translation

Logical properties from the first commit: `margin-inline`, `padding-inline`, `inset-inline`,
`text-align: start`. Never `left` or `right`. Icons that encode direction are mirrored via
`:dir(rtl)`.

This costs nothing now and is expensive across a built UI later. Arabic ships as a supported
layout with English strings until translation is justified by demand.

## 3. Turkish text handling

The single most dangerous class of silent bug in the system.

**Never call locale-naive casing.** `upper()`, `toUpperCase()`, `casefold()` on Turkish text
produce wrong results: `i` uppercases to `İ` in Turkish and `I` elsewhere, and `I` lowercases to
`ı`. A lexicon key built with the wrong casing silently fails to match, and nothing raises. CI
greps for these and fails the build. (ADR-0025)

**One fold function**, in `core`, applied identically on index and query side:

```
ı, İ -> i    ş -> s    ğ -> g    ç -> c    ö -> o    ü -> u
```

plus case normalisation under `tr_TR`, whitespace collapse, and trailing quantity artifact
stripping.

**The fold has exactly two consumers**: lexicon keys and trigram matching. It is deliberately
lossy.

**It is never applied to embedding input.** Stripping diacritics degrades a model trained on
natural text. `product_search_docs` carries `lexical_text` (folded) and `semantic_text`
(unfolded) as separate columns precisely so the two paths cannot be confused.

Postgres `unaccent` alone is insufficient, since it does not handle the dotless i correctly. The
fold is implemented in application code and mirrored as an immutable SQL function for index
expressions.

Turkish collation (`tr-TR-x-icu`) applies to display ordering, which is a different concern from
matching and must not be conflated with it.

## 4. Cross-language retrieval

The hard cases have zero character overlap:

| Query | Catalog | Overlap |
|---|---|---|
| `Käse` | `PEYNİR` | none |
| `гречка` | `KARABUĞDAY` | none |
| `Vollkornbrot` | `TAM BUĞDAY EKMEĞİ` | none |
| `tvorog` | `LOR PEYNİRİ` | none |
| `Emmentaler` | `EMMENTAL` | high |

Only the last is reachable by fuzzy string matching, which is why lexical search alone cannot
work here. Dense multilingual embeddings carry the load; trigram and exact matching carry brands,
barcodes and SKUs. Fused by reciprocal rank fusion, both inside Postgres. (ADR-0024)

Query locale is logged on every search. A zero-result query followed within a session by a
successful reformulation and a click is a labelled synonym pair, which fills the alias override
layer without anyone writing translations. (ADR-0039)

## 5. Taxonomy translation

The category tree is fully translated into all four locales. Around 150 nodes, bounded work, and
it is what makes browse and filter usable when product names are Turkish only.

It is not the answer to search, which is dense retrieval. It is the answer to navigation, which
search does not replace. (ADR-0037)

`categories.name_i18n` is JSONB keyed by locale, with `tr` required and others validated for
completeness by CI before a taxonomy version can be marked active.

## 6. Formatting

Delegated to ICU, never hand-rolled.

| Concern | Rule |
|---|---|
| Decimal separator | Turkish uses comma. Never assume a point |
| Currency | Symbol placement and spacing vary by locale. Format from `{amount_minor, currency}`, never from a pre-formatted string |
| Dates | Locale-formatted for display; ISO 8601 UTC on the wire, always |
| Numbers | Grouping separators differ. Never format server-side for display |
| Pluralisation | ICU plural categories. Russian has four; hardcoded singular and plural branches are wrong |

Money crosses the wire as `{ "amount_minor": 4590, "currency": "TRY" }` and is formatted at the
edge. A server that formats money for display has to know the viewer's locale, which is exactly
the coupling this avoids.

## 7. Locale negotiation

Order of precedence: explicit user setting, then `users.locale`, then `Accept-Language`, then
`tr`.

Turkish is the fallback rather than English because the largest user segment reads Turkish and
the content is Turkish regardless.

Locale is a user attribute, not a device attribute. A contributor who sets Russian on the phone
sees Russian in the browser too.

## 8. What is not translated

Stated so it is a decision rather than a gap.

- Product canonical names. Turkish, with aliases as an override layer.
- Receipt raw text. Immutable by definition.
- Brand names. Locale-invariant.
- Operator console. LTR, TR and EN only.
- Published index methodology documents. English, since the audience is press and researchers.

## 9. CI gates

| Gate | Fails when |
|---|---|
| `i18n-parity` | A locale file is missing keys present in another |
| `no-literal-strings` | A UI component contains a user-visible literal |
| `no-naive-casing` | `upper()`, `toUpperCase()` or `casefold()` appears on a text path |
| `taxonomy-i18n-complete` | A taxonomy version is marked active with incomplete `name_i18n` |
| `no-server-formatting` | A response field contains a pre-formatted number, currency or date |
