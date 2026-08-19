from __future__ import annotations

import pytest

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.modules.identity.models import PushPlatform, UserRole, UserStatus


class Colour(SqlStrEnum):
    RED = "red"
    BLUE = "blue"


class Single(SqlStrEnum):
    ONLY = "only"


def test_values_render_in_declaration_order() -> None:
    """Not sorted. Declaration order is what a reader of the class sees, and
    sorting would make a reordered class produce an unchanged constraint."""
    assert Colour.sql_values() == "'red', 'blue'"


def test_check_expression_is_ready_for_a_check_constraint() -> None:
    assert Colour.sql_check("colour") == "colour IN ('red', 'blue')"


def test_single_member_enum_renders_valid_sql() -> None:
    """Formatting a one-element Python tuple gives `IN ('only',)`, which is a
    syntax error. This is the reason the helper exists."""
    assert Single.sql_check("kind") == "kind IN ('only')"


def test_a_value_that_would_need_escaping_fails_at_import() -> None:
    """Values go straight into a SQL literal, so the alphabet is restricted and
    the failure happens at class definition rather than at migration."""
    with pytest.raises(ValueError, match="not usable as a SQL literal"):

        class Bad(SqlStrEnum):
            APOSTROPHE = "it's"


def test_members_are_usable_as_plain_strings() -> None:
    """`StrEnum`, so a member can be a server default or compared to a column
    value without anyone remembering to call `.value`."""
    assert UserRole.CONTRIBUTOR == "contributor"
    assert f"{UserStatus.ACTIVE}" == "active"


def test_identity_constraints_match_what_migration_0001_created() -> None:
    """These exact strings are in migration 0001 and in the applied database.
    The retrofit from tuples to enums must not have moved a character; if it
    did, the models and the schema disagree and autogenerate proposes a change
    on every run."""
    assert UserRole.sql_check("role") == (
        "role IN ('contributor', 'moderator', 'operator', 'admin')"
    )
    assert UserStatus.sql_check("status") == "status IN ('active', 'suspended', 'deleted')"
    assert PushPlatform.sql_check("platform") == "platform IN ('ios', 'android')"
