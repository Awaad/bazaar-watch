"""Fixture: bounty payout counting observations in raw SQL.

`economy` is restricted for observations and not for branches. Paying a
contributor twice for a receipt that was reprocessed is the same defect as
double counting it in an index.
"""

QUERY = "SELECT count(*) FROM price_observations WHERE branch_id = $1"
