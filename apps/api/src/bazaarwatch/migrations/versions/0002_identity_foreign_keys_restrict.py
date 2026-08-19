"""Identity foreign keys declare ON DELETE RESTRICT

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

`docs/03-data-model.md` section 1 says foreign keys are `ON DELETE RESTRICT` by
default. Migration 0001 declared none, so the identity keys were created with
NO ACTION. Practically the two behave alike here, since deletion is not a thing
this system does at all: the difference is that NO ACTION can be deferred to the
end of a transaction and RESTRICT cannot.

The reason to fix it is not the runtime behaviour. It is that `geo` is about to
add nine more foreign keys, and one convention applied everywhere is worth more
than the effort of aligning three constraints. Two patterns in one schema means
every later author has to guess which one is intended.

Postgres has no ALTER CONSTRAINT for this, so each key is dropped and recreated.
The tables are small and the operation takes a brief ACCESS EXCLUSIVE lock; on
a table with real traffic this would want more care than it does today.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, constraint name, column). Names are the ones migration 0001 declared
# explicitly, which are also what the fk naming convention produces.
_USER_FOREIGN_KEYS = (
    ("subject_keys", "fk_subject_keys_user_id_users", "user_id"),
    ("contributor_trust", "fk_contributor_trust_user_id_users", "user_id"),
    ("push_tokens", "fk_push_tokens_user_id_users", "user_id"),
)


def upgrade() -> None:
    for table, name, column in _USER_FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "users", [column], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    """Back to NO ACTION, which is what omitting the clause produces."""
    for table, name, column in _USER_FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "users", [column], ["id"])
