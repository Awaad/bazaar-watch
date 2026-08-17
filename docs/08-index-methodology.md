# 08. Index Methodology

Any figure we publish will eventually be quoted by someone who did not read this document,
and challenged by someone who did. The methodology is therefore fixed, versioned, and
stated in full before the first figure ships. (ADR-0029)

## 1. Two consumers, two instruments

Conflating them is the most common way price data becomes useless.

| Consumer | Wants | Instrument |
|---|---|---|
| Public, press, researchers | One defensible series over time | A price **index**, base period 100 |
| A shopper | Where to buy what, today, nearby | The **split basket** (ADR-0036), which is arithmetic over current observations, not an index |

The index answers "have prices risen". It never answers "where should I shop". A chain-level
index is a statement about a chain's basket over time, not a shopping recommendation, and
it is not presented as one.

## 2. Structure

Two levels, because expenditure weights only exist above a certain level of aggregation.

### Elementary aggregates

The lowest level: one product at one branch, or one product across the branches of one
chain. No weights exist here.

**Jevons index**, the geometric mean of price relatives:

```
I_jevons = product over items of (p_t / p_0) ^ (1/n)
```

Jevons is the international standard at this level because it is transitive and handles
substitution behaviour sensibly. **Carli**, the arithmetic mean of relatives, is not used:
it carries a well documented upward bias.

### Higher-level aggregation

Elementary indices are combined with expenditure weights in a Laspeyres-type structure, and
the series is **chained** so the basket can be updated without breaking continuity:

```
I_t = I_{t-1} * ( sum over strata of w_s * (I_s,t / I_s,t-1) )
```

Weights are refreshed on a fixed cycle. Chaining means a refresh does not create a
discontinuity.

## 3. Weights

Receipts carry quantities, so the corpus is expenditure data, not merely price data (ADR-0076). Weights
are derived from observed baskets and refreshed continuously. This is an advantage over
conventional practice, where statistical offices obtain weights from an annual household
expenditure survey that is their most expensive input.

`basket_items.weight_source` records the provenance of each weight:

| Source | Use |
|---|---|
| `observed_expenditure` | Derived from the corpus. Preferred. |
| `coicop_reference` | Published reference weights, used where corpus coverage is too thin |
| `manual` | Operator override, requires a recorded reason |

The taxonomy maps to **COICOP** division 01 and its subdivisions. The mapping costs little
at design time and is most of what makes the figures comparable to official statistics.

## 4. Missing prices

A branch will lack a recent observation for some basket items in some periods. The policy
is stated on every run in `index_runs.missing_policy`.

**Class mean imputation** is the default: the missing relative is imputed from the mean
relative of its elementary class in the same period.

**Carry-forward is not used.** Repeating last period's price is what naive implementations
do, and it systematically dampens the index toward zero change, which is precisely the wrong
bias in a high-inflation setting.

`index_values.imputed_pct` is published alongside every value. A figure resting largely on
imputation is disclosed as such rather than presented as measurement.

## 5. Staleness

There is no such thing as "the price". Every observation has an age.

`index_runs.staleness_window_days` defines eligibility: observations older than the window
do not enter the run and are handled as missing. `index_values.staleness_days_p50` is
published so a reader can judge how current the underlying data is.

## 6. Currency basis

North Cyprus runs on multiple currencies. One blended number would serve nobody, so two
labelled series are published, distinguished by `index_values.series_basis` (ADR-0078).

**`try_nominal`** is the primary series. TRY inflation is what a TRY-earning household
experiences, and an index of price relatives with base 100 is by construction immune to the
nominal-level confusion that makes raw price comparison across time misleading.

**`fx_deflated`** is secondary, for the substantial segment earning in GBP, EUR or USD. It
uses recorded rates from `fx_rates` with their `as_of` dates, so any published value is
reproducible.

Neither series is presented as the real one. They answer different questions for different
households.

## 7. Substitution and product churn

Products disappear. Packaging changes. A 1L bottle becomes 900ml at the same price, which is
a price rise that a naive comparison records as no change.

- `product_groups` defines admissible substitutes within an elementary aggregate.
- Net content is a required field on any `active` product, so shrinkflation is detected as a
  unit-price movement rather than missed.
- A replacement entering the basket is linked by overlap where a period of concurrent
  pricing exists, and by class mean imputation where it does not.
- Basket membership requires a **verified** product. A scraped, unverified row must never enter a
  published basket, enforced by trigger rather than by convention (ADR-0046).
- Private label never substitutes across chains (`owner_chain_id`), because it is not the
  same good.

## 8. Governance

Methodology changes are the point at which published statistics lose credibility, so the
process is fixed in advance.

1. **Every run records its methodology.** `index_runs.methodology_version`,
   `taxonomy_version`, `staleness_window_days`, `missing_policy`. A value without them is
   not publishable.
2. **Announce before changing.** The change and its rationale are published before the first
   figure computed under it.
3. **Run both series in parallel for three cycles.** New and old are computed and published
   side by side.
4. **Publish a linking factor** so users can splice the two series.
5. **Sunset, do not delete.** The old series stays available permanently, marked superseded.
6. **Never restate a published figure.** A figure published under a given methodology stands
   as the historical record. Corrections are issued as new figures with an erratum, never by
   silently rewriting the past.

A taxonomy restructure is a methodology change, because it alters what a category index
means even when no formula changed.

## 9. Stated limitations

Published in full alongside the figures. A critic will find these regardless, and finding
them already disclosed is the difference between a caveat and a scandal.

**The sample is not random.** Contributors self-select, skew urban, skew toward whichever
cells carry bounties (ADR-0020), and cluster around where contributors live. This is the
principal threat to the validity of every figure here and it does not go away with volume.
Post-stratification is the eventual mitigation and it requires population data we do not
yet have.

**Coverage is uneven across branches and categories.** `coverage_pct` is published per
value. Values below a stated coverage floor are suppressed rather than published thin.

**Promotional prices are excluded from the index** by `price_kind`, because a promotion is
not the shelf price and mixing them silently corrupts the series. They remain fully visible
in item-level lookup, where they are exactly what a shopper wants.

**Online branches are excluded** (ADR-0045). An online seller's pricing is not evidence
about the physical market.

**Unverified branches are excluded** (ADR-0023).

**We are not a statistical office.** These figures are derived from a crowdsourced corpus
with a documented methodology. They are not official statistics and are not presented as
equivalent to them.
