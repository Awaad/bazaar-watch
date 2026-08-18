from __future__ import annotations

from bazaarwatch.core.models import NAMING_CONVENTION, Base
from bazaarwatch.modules.identity import models as identity


def test_every_table_uses_the_shared_metadata() -> None:
    """One metadata object, or Alembic autogenerate sees a partial schema and
    proposes dropping whatever it cannot see."""
    tables = set(Base.metadata.tables)
    assert {
        "users",
        "subject_keys",
        "contributor_trust",
        "erasure_counters",
        "push_tokens",
    } <= tables


def test_naming_convention_is_applied() -> None:
    """Without it, Postgres invents constraint names, autogenerate produces
    different names on different machines, and a downgrade cannot reliably drop
    what an upgrade created."""
    assert Base.metadata.naming_convention == NAMING_CONVENTION
    users = Base.metadata.tables["users"]
    assert users.primary_key.name == "pk_users"


def test_phone_is_nullable_because_erasure_nulls_it() -> None:
    users = Base.metadata.tables["users"]
    assert users.c.phone_e164.nullable is True
    assert users.c.slug.nullable is False


def test_review_weight_has_no_server_default() -> None:
    """It is a tuning constant, and a DDL default is exactly where one must not
    hide. See ADR-0021."""
    trust = Base.metadata.tables["contributor_trust"]
    assert trust.c.review_weight.server_default is None
    assert trust.c.review_weight.nullable is False


def test_tombstone_identifier_is_fixed_and_wellformed() -> None:
    """Every environment must agree on it, since erasure points every severed
    reference here. See ADR-0084."""
    assert identity.TOMBSTONE_USER_ID.version == 7
    assert (identity.TOMBSTONE_USER_ID.int >> 62) & 0b11 == 0b10
    assert identity.TOMBSTONE_SLUG == "deleted-contributor"


def test_primary_keys_default_to_uuidv7_server_side() -> None:
    """The server default exists for fixtures and manual inserts and must
    produce the same insert locality as the application default."""
    for name in ("users", "push_tokens"):
        default = Base.metadata.tables[name].c.id.server_default
        assert default is not None
        assert "uuidv7()" in str(default.arg)
