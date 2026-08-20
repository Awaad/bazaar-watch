"""Fixture: raw SQL in a module that may not import geo at all.

Rule 1 cannot see inside a string, which is why there is a rule 2.
"""

from sqlalchemy import text

QUERY = text("SELECT d.id FROM product_search_docs d JOIN branches b ON b.id = d.branch_id")
