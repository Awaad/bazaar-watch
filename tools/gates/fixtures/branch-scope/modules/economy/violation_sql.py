"""Fixture: raw SQL outside geo, in a module the identifier rule does not cover.

Bounty payout is not an index, but a string naming the table still bypasses
both exclusions.
"""

QUERY = "UPDATE branches SET verified_by_human = TRUE"
