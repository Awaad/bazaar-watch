"""Submissions, media, extraction runs, receipts and receipt lines.

`receipt_lines` is append-only. A correction from review creates a new
extraction run rather than an update in place, because an observation that
changed silently is an observation nobody can audit (ADR-0006).

`extraction_runs` exists so a reprocessed corpus supersedes rather than
coexists. Without it, improving the model double-counts every receipt it
touches (ADR-0082).
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from bazaarwatch.core.enums import SqlStrEnum
from bazaarwatch.core.models import Base, created_at_column, updated_at_column, uuid_pk


class Channel(SqlStrEnum):
    APP = "app"
    CONSOLE = "console"
    SCRAPE = "scrape"


class SubmissionKind(SqlStrEnum):
    RECEIPT = "receipt"
    SHELF_MANUAL = "shelf_manual"
    SHELF_BARCODE = "shelf_barcode"


class SubmissionStatus(SqlStrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class MediaRole(SqlStrEnum):
    ORIGINAL = "original"
    CROP = "crop"


class ExtractionStatus(SqlStrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ReconciliationStatus(SqlStrEnum):
    UNCHECKED = "unchecked"
    BALANCED = "balanced"
    RESIDUAL = "residual"
    UNPARSEABLE = "unparseable"


class ReceiptStatus(SqlStrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class LineKind(SqlStrEnum):
    ITEM = "item"
    DISCOUNT = "discount"
    SUBTOTAL = "subtotal"
    TAX = "tax"
    TENDER = "tender"
    UNKNOWN = "unknown"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    contributor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Client-generated, so a retry over a bad connection replays rather than
    # duplicates. Unique, which is what makes the replay detectable.
    client_idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    claimed_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("branches.id", ondelete="RESTRICT")
    )
    captured_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # Derived at ingest. The coordinate itself is discarded: keeping it would
    # make every submission a location history of the contributor.
    location_matched: Mapped[bool | None] = mapped_column(Boolean)
    location_confidence: Mapped[Decimal | None] = mapped_column(Numeric(precision=4, scale=3))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=SubmissionStatus.RECEIVED.value
    )
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()

    __table_args__ = (
        CheckConstraint(Channel.sql_check("channel"), name="channel_known"),
        CheckConstraint(SubmissionKind.sql_check("kind"), name="kind_known"),
        CheckConstraint(SubmissionStatus.sql_check("status"), name="status_known"),
        CheckConstraint(
            "location_confidence IS NULL OR location_confidence BETWEEN 0 AND 1",
            name="confidence_in_range",
        ),
        # A confidence with no verdict, or a verdict with no confidence, is half
        # a derivation and neither half is usable.
        CheckConstraint(
            "(location_matched IS NULL) = (location_confidence IS NULL)",
            name="location_verdict_is_complete",
        ),
        Index("ix_submissions_contributor_id", "contributor_id"),
        Index("ix_submissions_status", "status"),
    )


class MediaObject(Base):
    """Encrypted at rest under a key wrapped by the subject's KEK.

    Crops share the subject of their original. Shredding an original while its
    crops persist would retain fragments of exactly the sensitive content the
    shredding was for (ADR-0084).
    """

    __tablename__ = "media_objects"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("submissions.id", ondelete="RESTRICT")
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    bucket: Mapped[str] = mapped_column(String(63), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    reencoded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    subject_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # The data key, wrapped by the subject KEK. Erasure destroys the KEK, which
    # makes every object wrapped by it unreadable without touching the bytes.
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(MediaRole.sql_check("role"), name="role_known"),
        CheckConstraint("byte_size > 0", name="byte_size_is_positive"),
        # Dimensions come as a pair or not at all.
        CheckConstraint("(width IS NULL) = (height IS NULL)", name="dimensions_are_paired"),
        CheckConstraint(
            "width IS NULL OR (width > 0 AND height > 0)", name="dimensions_are_positive"
        ),
        CheckConstraint("length(wrapped_dek) > 0", name="dek_is_present"),
        UniqueConstraint("bucket", "object_key", name="uq_media_objects_location"),
        Index("ix_media_objects_subject_user_id", "subject_user_id"),
        # Identical bytes mean an identical image. The confirm endpoint links to
        # the existing row rather than erroring.
        Index(
            "ix_media_objects_content_hash",
            "content_hash",
            postgresql_where=text("role = 'original'"),
        ),
    )


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("extraction_runs.id", ondelete="RESTRICT")
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ExtractionStatus.RUNNING.value
    )

    __table_args__ = (
        CheckConstraint(ExtractionStatus.sql_check("status"), name="status_known"),
        # A superseded run is not the current one. Without this, superseding
        # without clearing the flag leaves two current runs and the partial
        # index below is the only thing that notices, at a confusing moment.
        CheckConstraint(
            "NOT is_current OR status <> 'superseded'", name="superseded_is_not_current"
        ),
        CheckConstraint(
            "superseded_by IS NULL OR superseded_by <> id", name="not_its_own_successor"
        ),
        CheckConstraint(
            "superseded_by IS NULL OR status = 'superseded'",
            name="successor_implies_superseded",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="completed_after_started"
        ),
        UniqueConstraint(
            "submission_id",
            "extraction_method",
            "extraction_version",
            name="uq_extraction_runs_attempt",
        ),
        # Exactly one current run per submission. This is what makes
        # reprocessing supersede rather than double count (ADR-0082).
        Index(
            "uq_extraction_runs_current",
            "submission_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=False
    )
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("extraction_runs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("branches.id", ondelete="RESTRICT")
    )
    receipt_datetime: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    printed_total_minor: Mapped[int | None] = mapped_column(BigInteger)
    # KDV breakdown. Informational, and never an addend: adding it to the line
    # total double-counts tax that is already inside every printed price.
    tax_total_minor: Mapped[int | None] = mapped_column(BigInteger)
    discount_total_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="TRY")
    fingerprint: Mapped[str | None] = mapped_column(String(128))
    reconciliation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ReconciliationStatus.UNCHECKED.value
    )
    reconciliation_residual_minor: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=ReceiptStatus.PENDING.value
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(
            ReconciliationStatus.sql_check("reconciliation_status"),
            name="reconciliation_status_known",
        ),
        CheckConstraint(ReceiptStatus.sql_check("status"), name="status_known"),
        # A residual verdict with no residual is a verdict nobody can check.
        CheckConstraint(
            "reconciliation_status <> 'residual' OR reconciliation_residual_minor IS NOT NULL",
            name="residual_is_quantified",
        ),
        CheckConstraint(
            "printed_total_minor IS NULL OR printed_total_minor >= 0",
            name="printed_total_is_not_negative",
        ),
        Index("ix_receipts_fingerprint", "fingerprint"),
        Index("ix_receipts_submission_id", "submission_id"),
    )


class ReceiptLine(Base):
    """Append-only. A correction creates a new extraction run (ADR-0006)."""

    __tablename__ = "receipt_lines"

    id: Mapped[uuid.UUID] = uuid_pk()
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    line_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Verbatim and immutable. Everything else on this row is an interpretation
    # of it, and an interpretation you cannot check against the original is a
    # claim rather than a reading.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    interpreted_text: Mapped[str | None] = mapped_column(Text)
    sku_text: Mapped[str | None] = mapped_column(String(200))
    raw_quantity: Mapped[Decimal | None] = mapped_column(Numeric(precision=12, scale=4))
    raw_uom: Mapped[str | None] = mapped_column(String(16))
    raw_unit_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    raw_line_total_minor: Mapped[int | None] = mapped_column(BigInteger)
    # The KDV rate printed beside the line, in basis points: 0, 500, 1000, 1600.
    #
    # Basis points as an integer, because rates print as whole percents and an
    # integer is exact where a fraction invites a float.
    #
    # Nullable: not every POS prints a per-line rate, and its absence is a fact
    # about the chain rather than an error.
    #
    # Stored because it cannot be recovered later. Every other field on this row
    # can be re-read from the image; the rate that applied to this transaction
    # cannot be reconstructed from the mapped product's category and the date,
    # and that reconstruction fails exactly across a rate change, which is the
    # only time anyone would ask. Once the ADR-0016 retention window deletes the
    # original, whatever is not in a column is gone.
    #
    # It also turns reconciliation from one equation into one per rate bucket.
    # ADR-0081 compares one sum to one total, which compensating errors survive;
    # an error that preserves the grand total rarely preserves every bucket.
    tax_rate_bp: Mapped[int | None] = mapped_column(SmallInteger)
    # [x, y, w, h] normalised. Required for T2 crops, which is why the bake-off
    # scores box quality: cropped review is impossible without it.
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    modifies_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("receipt_lines.id", ondelete="RESTRICT")
    )
    created_at: Mapped[dt.datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(LineKind.sql_check("line_kind"), name="line_kind_known"),
        CheckConstraint("line_index >= 0", name="line_index_is_not_negative"),
        CheckConstraint("length(raw_text) > 0", name="raw_text_is_not_empty"),
        CheckConstraint(
            "modifies_line_id IS NULL OR modifies_line_id <> id", name="does_not_modify_itself"
        ),
        # Four normalised numbers. A three-element box crops the wrong region
        # and a reviewer sees an arbitrary strip of someone's receipt.
        CheckConstraint(
            "bbox IS NULL OR jsonb_array_length(bbox) = 4", name="bbox_has_four_values"
        ),
        CheckConstraint(
            "tax_rate_bp IS NULL OR tax_rate_bp BETWEEN 0 AND 10000",
            name="tax_rate_in_range",
        ),
        UniqueConstraint("receipt_id", "line_index", name="uq_receipt_lines_index"),
    )


__all__ = [
    "Channel",
    "ExtractionRun",
    "ExtractionStatus",
    "LineKind",
    "MediaObject",
    "MediaRole",
    "Receipt",
    "ReceiptLine",
    "ReceiptStatus",
    "ReconciliationStatus",
    "Submission",
    "SubmissionKind",
    "SubmissionStatus",
]
