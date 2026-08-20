"""Fixture: a second revision reusing the same constant name.

Realistic, because every revision that adds mutable tables wants the same name
for its tuple. Resolving the constant against the concatenated source finds the
first assignment and silently reports the later revision's tables as uncovered.
Both files below must come back covered.
"""

_UPDATED_AT_TABLES = ("gadgets",)


def upgrade() -> None:
    op.create_table(
        "gadgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gadgets"),
    )

    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
