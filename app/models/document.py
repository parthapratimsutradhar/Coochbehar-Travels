import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DocumentType
from app.models.base import ActiveEntity


class Document(ActiveEntity):
    __tablename__ = "documents"

    """
    Stores uploaded documents for customers and internal/admin use.

    Ownership:
        customer_id -> Customer the document belongs to.

    Upload audit:
        uploaded_by_user_id -> Admin/staff who uploaded it.
        uploaded_by_customer_id -> Customer who uploaded it.

    Delete audit:
        deleted_by_user_id -> Admin/staff who deleted it.
        deleted_by_customer_id -> Customer who deleted it.

    Soft deletion:
        is_active = False
        deleted_at = deletion timestamp

    The original uploader information is preserved even after deletion.
    """

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ── Owner ──────────────────────────────────────────────────────

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ── Upload audit ──────────────────────────────────────────────

    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    uploaded_by_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── File information ──────────────────────────────────────────

    file_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # ── Delete audit ──────────────────────────────────────────────

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    deleted_by_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ── Relationships ─────────────────────────────────────────────

    customer = relationship(
        "Customer",
        foreign_keys=[customer_id],
        back_populates="documents",
    )

    uploaded_by_user = relationship(
        "User",
        foreign_keys=[uploaded_by_user_id],
        back_populates="documents_uploaded",
    )

    uploaded_by_customer = relationship(
        "Customer",
        foreign_keys=[uploaded_by_customer_id],
        back_populates="documents_uploaded",
    )

    deleted_by_user = relationship(
        "User",
        foreign_keys=[deleted_by_user_id],
        back_populates="documents_deleted",
    )

    deleted_by_customer = relationship(
        "Customer",
        foreign_keys=[deleted_by_customer_id],
        back_populates="documents_deleted",
    )