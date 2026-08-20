"""Fixture: triggers created in a loop over a module constant.

Correct, and the gate could not see it before. The f-string in the loop never
spells the trigger name out, so a search for the literal finds nothing.
"""

_UPDATED_AT_TABLES = ("widgets",)


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

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
