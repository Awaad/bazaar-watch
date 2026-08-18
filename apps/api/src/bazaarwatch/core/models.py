"""Declarative base and shared column conventions.

`core` owns the base so every module inherits one metadata object and one
naming convention. It imports no domain module.

The naming convention is not cosmetic. Without it, Postgres invents constraint
names, Alembic autogenerate produces different names on different machines, and
a downgrade cannot reliably drop what an upgrade created.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bazaarwatch.core.ids import new_id

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> Mapped[uuid.UUID]:
    """Primary key column.

    The Python default is authoritative; the server default exists for
    fixtures and manual inserts, and produces the same insert locality because
    Postgres 18 has native uuidv7(). See ADR-0003.
    """
    return mapped_column(
        primary_key=True,
        default=new_id,
        server_default=text("uuidv7()"),
    )


def created_at_column() -> Mapped[dt.datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def updated_at_column() -> Mapped[dt.datetime]:
    """Maintained by a database trigger, not by the application.

    An application-maintained timestamp is wrong the moment anything writes
    outside the ORM, which migrations and operational fixes both do.
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
