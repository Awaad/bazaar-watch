"""Fixture: a mutable table whose updated_at nothing maintains.

No error, no test failure. The column takes its DEFAULT now() on insert and
then never changes again, and nobody notices for months.
"""


def upgrade() -> None:
    op.create_table(
        "widgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_widgets"),
    )
