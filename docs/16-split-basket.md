# 16. Split Basket

The consumer surface. Given a shopping list, a store-count budget and a reachability constraint,
return where to buy what.

This is arithmetic over current observations, not a recommendation problem. It has no model, and it
must be explainable to a user who disputes it. (ADR-0036)

## 1. What it is not

**Not a store league table.** "Which shop is cheapest" is only actionable if the ordering is stable
and unconditional, and it is neither: chain tendencies are real but conditional on category
(ADR-0034).

**Not the index.** The index answers "have prices risen" over time, with a fixed basket, excluding
promotions, excluding online and unverified branches. The split basket answers "where do I buy this
today", with the user's own list, including promotions. Same data, different instruments, and
conflating them produces something that serves neither (ADR-0029).

## 2. Inputs

| Input | Source | Default |
|---|---|---|
| List | User, as canonical products or product groups | required |
| Origin | Device location or a saved address | required |
| Reachability radius | User setting | from `tuning.json` |
| Store-count budget | User setting: how many shops they will visit | 2 |
| Staleness tolerance | User setting | from `tuning.json` |

The store-count budget is what makes this a real optimisation rather than a lookup. With a budget of
one it degenerates to "cheapest single shop for this list", which is a legitimate answer and often
what a user wants.

## 3. Reachable set

Computed before anything else, never after.

```sql
SELECT b.* FROM branches b
WHERE b.branch_kind = 'physical'
  AND b.verified_by_human
  AND b.operating_status = 'open'
  AND ST_DWithin(b.geom, :origin, :radius_m)
```

Three exclusions, each with its own reason:

- `physical` only. Reachability is meaningless for an online seller (ADR-0045).
- `verified_by_human` only. A mis-pinned branch places itself inside or outside the reachable set
  incorrectly, which corrupts the result rather than merely misplacing a dot (ADR-0023).
- `operating_status = 'open'`. A permanently closed shop with cheap historical prices would win.

Radius is a crude proxy for travel time. It is correct enough at city scale and requires no routing
dependency. An isochrone is the eventual refinement (ADR-0035).

## 4. Price selection

For each `(branch, product)` cell in the reachable set, the most recent observation within the
staleness tolerance.

```sql
SELECT DISTINCT ON (branch_id, product_id) ...
FROM price_observations
WHERE branch_id = ANY(:reachable)
  AND product_id = ANY(:list)
  AND status = 'accepted'
  AND observed_at > now() - :staleness
ORDER BY branch_id, product_id, observed_at DESC
```

**Promotional prices are included here**, unlike in the index. A promotion is not a shelf price for
index purposes, but it is exactly what a shopper wants to know about. `price_kind` is surfaced on the
result so the user knows it may not hold.

`status = 'accepted'` excludes provisional and flagged observations. A provisional price could be
wrong and a shopper acting on it would be misled.

Every returned price carries `observed_at` and `staleness_days`. There is no surface in this system
that shows a price without its age (ADR-0029).

## 5. Assignment

With a store-count budget of `k` over `n` reachable branches, this is a set-cover-flavoured problem.
At realistic sizes it is not a hard one.

```
candidates = all combinations of up to k branches from the reachable set
for each combination:
    for each list item:
        pick the cheapest available price among those branches
    cost = sum of picked prices
    coverage = items found / items requested
rank by (coverage desc, cost asc)
```

`n` is tens of branches and `k` is two or three, so exhaustive enumeration over combinations is a few
thousand evaluations. There is no need for a heuristic and no justification for one, since an exact
answer is both cheap and explainable.

Ties on cost break on fewer stores, then on shorter total distance.

## 6. Missing items

Stated policy, because it is a product decision with visible consequences.

An item with no price in any reachable branch is returned as **missing**, with the reason: no
observation, all observations stale, or the product exists but has never been seen at any reachable
branch.

It is never silently dropped from the total, and it is never imputed. Imputation is an index
technique for producing a comparable series (ADR-0077); presenting an imputed price to a shopper as
if it were real would be a lie.

Missing items make coverage gaps visible to users, which is honest and also generates exactly the
demand signal that bounties respond to (ADR-0020).

## 7. Substitution

Strict matching by default. Alternatives are offered, never applied. (ADR-0041)

An alternative is surfaced when:

- another product in the same `product_group` is available at a lower **unit price**, or
- the same product in a different pack size has a better unit price.

Each alternative is presented with the unit-price comparison that justifies it, and requires one
explicit action to accept.

Private label never substitutes across chains, because it is not the same good (ADR-0007).

The reasoning: a recommendation the user did not expect costs more trust than the saving is worth,
and a user who wants the saving can take it in one tap.

## 8. Output

```json
{
  "stops": [
    { "branch": {...}, "items": [
        { "product": {...},
          "price": { "amount_minor": 4590, "currency": "TRY" },
          "unit_price": { "amount_minor": 4590, "currency": "TRY", "basis": "per_l" },
          "price_kind": "regular",
          "observed_at": "2026-08-14T09:12:00Z",
          "staleness_days": 2,
          "alternatives": [...] } ] }
  ],
  "missing": [ { "product": {...}, "reason": "no_recent_observation" } ],
  "total": { "amount_minor": 41230, "currency": "TRY" },
  "coverage_pct": 87.5,
  "compared_branches": 9
}
```

`compared_branches` matters: a split computed over three reachable branches is a much weaker answer
than one computed over twelve, and the user should be able to see that.

## 9. Honest limits

**It depends entirely on coverage for the user's specific list and reachable set.** A thin corpus
produces a thin answer, and the response says so through `coverage_pct` and the missing list rather
than guessing.

**Prices are observations, not guarantees.** Under high inflation a two-day-old price may already be
wrong. This is why staleness travels with every price rather than being available on request.

**It optimises cost, not time or preference.** It does not know that one shop has better produce,
which is what the structured store attributes are for (ADR-0052), and it does not model traffic.

**Promotions may have ended.** Included because they are useful, labelled because they are
unreliable.
