"""Identity tables.

Owned by this module. No other module imports these; cross-module access goes
through `service.py`. See docs/15-repo-structure-standards.md section 2.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.models import Base, created_at_column, updated_at_column, uuid_pk
from bazaarwatch.core.text import SLUG_MAX_LENGTH

# All erased contributor references point here. A unique identifier per erased
# user would keep their submissions mutually linkable, which is
# pseudonymisation rather than anonymisation and leaves the obligation intact.
# See ADR-0084.
TOMBSTONE_USER_ID = uuid.UUID("00000000-0000-7000-8000-000000000000")
TOMBSTONE_SLUG = "deleted-contributor"


class UserRole(SqlStrEnum):
    CONTRIBUTOR = "contributor"
    MODERATOR = "moderator"
    OPERATOR = "operator"
    ADMIN = "admin"


class UserStatus(SqlStrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    # Set on erasure. The row survives, stripped, because references repoint to
    # the tombstone rather than cascading. See ADR-0084.
    DELETED = "deleted"


class PushPlatform(SqlStrEnum):
    IOS = "ios"
    ANDROID = "android"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Length comes from core.text, so a generated slug cannot outgrow the
    # column that stores it.
    slug: Mapped[str] = mapped_column(String(SLUG_MAX_LENGTH), nullable=False, unique=True)
    # Nullable because erasure nulls it. Tier C under ADR-0071: deleted
    # outright, not shredded and not severed.
    phone_e164: Mapped[str | None] = mapped_column(String(20), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default="tr")
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=UserRole.CONTRIBUTOR.value
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=UserStatus.ACTIVE.value
    )
    erased_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    is_tombstone: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(UserRole.sql_check("role"), name="role_known"),
        CheckConstraint(UserStatus.sql_check("status"), name="status_known"),
        CheckConstraint(
            "erased_at IS NULL OR (phone_e164 IS NULL AND display_name IS NULL)",
            name="erased_users_are_stripped",
        ),
        Index(
            "uq_users_single_tombstone",
            "is_tombstone",
            unique=True,
            postgresql_where=text("is_tombstone"),
        ),
    )


class SubjectKey(Base):
    """Per-subject key encrypting key.

    Erasure destroys the KEK, rendering every media object under it permanently
    unreadable including in immutable replicas and versioned objects that
    ordinary deletion cannot reach. See ADR-0071, ADR-0086.
    """

    __tablename__ = "subject_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    kek_ref: Mapped[str | None] = mapped_column(Text)
    shredded_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint("shredded_at IS NULL OR kek_ref IS NULL", name="shredded_has_no_ref"),
    )


class ContributorTrust(Base):
    """Derived, recomputed on adjudication. Never edited by hand.

    `review_weight` has no server default: it is seeded from tuning.json at
    insert, because a DDL default is exactly where a tuning constant must not
    hide. See ADR-0021.
    """

    __tablename__ = "contributor_trust"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    submission_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    review_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    review_weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    submissions_total: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reviews_total: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    updated_at: Mapped[dt.datetime] = updated_at_column()


class ErasureCounter(Base):
    """Erasures are counted, not identified. See ADR-0084."""

    __tablename__ = "erasure_counters"

    period_month: Mapped[dt.date] = mapped_column(primary_key=True)
    erasures: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class PushToken(Base):
    """Tier C under ADR-0071: deleted outright on erasure."""

    __tablename__ = "push_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(8), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_seen_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(PushPlatform.sql_check("platform"), name="platform_known"),
        Index("uq_push_tokens_platform_token", "platform", "token", unique=True),
        Index(
            "ix_push_tokens_user_id_enabled",
            "user_id",
            postgresql_where=text("enabled"),
        ),
    )


__all__ = [
    "TOMBSTONE_SLUG",
    "TOMBSTONE_USER_ID",
    "ContributorTrust",
    "ErasureCounter",
    "PushPlatform",
    "PushToken",
    "SubjectKey",
    "User",
    "UserRole",
    "UserStatus",
]
