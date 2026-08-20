"""Fixture: correct migration, formatted in ways the old regexes could not read.

Every earlier version of this gate matched text. This file closes
`op.create_table(...)` on the same line as its last argument and wraps the table
tuple across lines, both of which are legal, both of which ruff will produce, and
neither of which changes what the migration does. The gate reported the tables as
uncovered.

Formatting is not something a gate should have opinions about.
"""

_UPDATED_AT_TABLES = (
    "widgets",
    "sprockets",
)


def upgrade() -> None:
    op.create_table(
        "widgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_widgets"))

    op.create_table(
        "sprockets", sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
