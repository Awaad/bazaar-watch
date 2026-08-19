from __future__ import annotations

from bazaarwatch.core.models import Base
from bazaarwatch.modules.identity import models as _identity  # noqa: F401


def test_every_foreign_key_declares_on_delete_restrict() -> None:
    """`docs/03-data-model.md` section 1: RESTRICT by default. Migration 0001
    omitted it, which left the identity keys on NO ACTION, and migration 0002
    aligned them. One convention across the schema, so a later author does not
    have to work out which of two patterns was meant."""
    undeclared = [
        f"{table.name}.{fk.parent.name} -> {fk.target_fullname}"
        for table in Base.metadata.tables.values()
        for fk in table.foreign_keys
        if fk.ondelete != "RESTRICT"
    ]
    assert not undeclared, f"foreign keys without ON DELETE RESTRICT: {undeclared}"


def test_there_are_foreign_keys_to_check() -> None:
    """The assertion above passes vacuously on an empty schema, which would
    hide the models failing to import."""
    keys = [fk for table in Base.metadata.tables.values() for fk in table.foreign_keys]
    assert len(keys) >= 3
