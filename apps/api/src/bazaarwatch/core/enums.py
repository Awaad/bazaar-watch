"""Enumerations that are enforced by a CHECK constraint.

Native Postgres enums are avoided: altering one is painful and they do not
generate cleanly. Every enumeration in this system is a Python `StrEnum`, with
the column typed `TEXT` and the vocabulary enforced by a `CHECK`. See
docs/03-data-model.md section 1.

Both halves come from one class here. A tuple of strings and a hand-written
constraint are two places that must agree with nothing checking that they do.

The column stays `Mapped[str]` rather than `Mapped[SomeEnum]`. Mapping the
Python type would mean `sa.Enum(..., native_enum=False)`, which emits its own
CHECK constraint and compares differently under `compare_type=True`, so
autogenerate would propose a change on every run. The enum is the vocabulary
and the constraint is the enforcement; the ORM is not asked to convert.
"""

from __future__ import annotations

import re
from enum import StrEnum

# Values are rendered directly into SQL string literals below. Restricting them
# to this alphabet means the rendering never has to quote or escape, and a value
# that would need escaping fails at import time rather than at migration time.
_SAFE_VALUE = re.compile(r"\A[a-z0-9_]+\Z")


class SqlStrEnum(StrEnum):
    """A `StrEnum` that can render its own `CHECK` constraint expression."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for member in cls:
            if not _SAFE_VALUE.match(member.value):
                raise ValueError(
                    f"{cls.__name__}.{member.name} = {member.value!r} is not usable as a "
                    "SQL literal. Enumeration values are lowercase ASCII words."
                )

    @classmethod
    def sql_values(cls) -> str:
        """The literal list for a CHECK, e.g. `'ios', 'android'`.

        Declaration order, not sorted: it is the order a reader of the class
        sees, and reordering the class would otherwise leave the constraint
        unchanged while the two look different.
        """
        return ", ".join(f"'{member.value}'" for member in cls)

    @classmethod
    def sql_check(cls, column: str) -> str:
        """A CHECK expression, e.g. `platform IN ('ios', 'android')`.

        A single-member enumeration renders `x IN ('only')`. Formatting a
        one-element Python tuple instead produces `x IN ('only',)`, which is a
        syntax error, and that is the whole reason this is a function rather
        than an f-string at each call site.
        """
        return f"{column} IN ({cls.sql_values()})"


__all__ = ["SqlStrEnum"]
