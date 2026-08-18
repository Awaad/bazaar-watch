"""Foundation and identity

Revision ID: 0001
Revises:
Create Date: 2026-08-17

Installs the objects everything else depends on, then the identity tables.

Extensions are asserted rather than created. CREATE EXTENSION requires
superuser, and granting that to the application role in production is not
acceptable; managed Postgres often forbids it outright. They are created by the
privileged initdb bootstrap in infra/docker/postgres. Asserting here means a
missing extension surfaces at migrate time with a clear message rather than at
first query. See infra/docker/postgres/README.md.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_EXTENSIONS = ("postgis", "vector", "pg_trgm", "ltree", "pgcrypto")

TOMBSTONE_USER_ID = "00000000-0000-7000-8000-000000000000"

# Read from the package rather than duplicated here. One definition, mirrored
# from bazaarwatch.core.text.turkish_fold, with parity asserted by test.
_TURKISH_FOLD_SQL = (
    Path(__file__).resolve().parents[2] / "core" / "sql" / "turkish_fold.sql"
).read_text(encoding="utf-8")

SET_UPDATED_AT = """
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;
"""


# Asserted in SQL rather than in Python, so the check works identically in
# online mode and in `--sql` offline mode, where there is no bind to query. One
# code path, and the failure is raised by the server that would have to run the
# rest of the migration anyway.
_EXTENSION_LIST = ", ".join(f"'{name}'" for name in REQUIRED_EXTENSIONS)

ASSERT_EXTENSIONS = f"""
DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(required, ', ' ORDER BY required)
      INTO missing
      FROM unnest(ARRAY[{_EXTENSION_LIST}]) AS required
     WHERE required NOT IN (SELECT extname FROM pg_extension);

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION
            'Required extensions are not installed: %. They are created by the '
            'privileged initdb bootstrap, not by Alembic. Locally: make db-reset. '
            'See infra/docker/postgres/README.md.', missing;
    END IF;
END
$$;
""".format(extensions=", ".join(f"'{name}'" for name in REQUIRED_EXTENSIONS))


def upgrade() -> None:
    op.execute(ASSERT_EXTENSIONS)

    op.execute(_TURKISH_FOLD_SQL)
    op.execute(SET_UPDATED_AT)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("locale", sa.String(length=8), server_default="tr", nullable=False),
        sa.Column("role", sa.String(length=16), server_default="contributor", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_tombstone", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('contributor', 'moderator', 'operator', 'admin')",
            name="role_known",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'deleted')",
            name="status_known",
        ),
        sa.CheckConstraint(
            "erased_at IS NULL OR (phone_e164 IS NULL AND display_name IS NULL)",
            name="erased_users_are_stripped",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("slug", name="uq_users_slug"),
        sa.UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
    )
    # Exactly one tombstone row, enforced rather than assumed. See ADR-0084.
    op.create_index(
        "uq_users_single_tombstone",
        "users",
        ["is_tombstone"],
        unique=True,
        postgresql_where=sa.text("is_tombstone"),
    )

    op.create_table(
        "subject_keys",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kek_ref", sa.Text(), nullable=True),
        sa.Column("shredded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "shredded_at IS NULL OR kek_ref IS NULL",
            name="shredded_has_no_ref",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_subject_keys_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_subject_keys"),
    )

    op.create_table(
        "contributor_trust",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("submission_accuracy", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("review_accuracy", sa.Numeric(precision=5, scale=4), nullable=True),
        # No server default: review_weight is a tuning constant and a DDL
        # default is exactly where one must not hide. See ADR-0021.
        sa.Column("review_weight", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("submissions_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reviews_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_contributor_trust_user_id_users"
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_contributor_trust"),
    )

    op.create_table(
        "erasure_counters",
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("erasures", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("period_month", name="pk_erasure_counters"),
    )

    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=8), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("platform IN ('ios', 'android')", name="platform_known"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_push_tokens_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_push_tokens"),
    )
    op.create_index(
        "uq_push_tokens_platform_token", "push_tokens", ["platform", "token"], unique=True
    )
    op.create_index(
        "ix_push_tokens_user_id_enabled",
        "push_tokens",
        ["user_id"],
        postgresql_where=sa.text("enabled"),
    )

    # updated_at is maintained by the database, not the application. An
    # application-maintained timestamp is wrong the moment anything writes
    # outside the ORM, which migrations and operational fixes both do.
    for table in ("users", "contributor_trust"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )

    # The tombstone. Seeded with a fixed identifier so every environment agrees
    # on it and erasure has somewhere to point.
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, slug, locale, role, status, is_tombstone)
            VALUES (:id, 'deleted-contributor', 'tr', 'contributor', 'active', true)
        """
        ).bindparams(id=uuid.UUID(TOMBSTONE_USER_ID))
    )


def downgrade() -> None:
    for table in ("contributor_trust", "users"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")

    op.drop_index("ix_push_tokens_user_id_enabled", table_name="push_tokens")
    op.drop_index("uq_push_tokens_platform_token", table_name="push_tokens")
    op.drop_table("push_tokens")
    op.drop_table("erasure_counters")
    op.drop_table("contributor_trust")
    op.drop_table("subject_keys")
    op.drop_index("uq_users_single_tombstone", table_name="users")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS turkish_fold(text);")
    # Extensions are not dropped. They were not created here, and dropping
    # postgis on a downgrade would take unrelated objects with it.
