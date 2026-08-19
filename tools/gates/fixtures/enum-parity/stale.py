"""Fixture: a migration set that creates a table and no vocabulary constraint.

Stands in for the real failure, which is an enum gaining a member while the
constraint in the database keeps the old list. The gate must report every
enum-backed CHECK the models describe as missing.
"""


def upgrade() -> None:
    op.create_table("users", sa.Column("role", sa.String(length=16)))
