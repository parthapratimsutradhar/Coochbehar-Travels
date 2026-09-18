import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import LeadLostReason, LeadStatus
from app.models.base import BaseEntity


class Lead(BaseEntity):
    __tablename__ = "leads"

    lead_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    assigned_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    lead_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.NEW,
        index=True,
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    qualified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lost_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lost_reason: Mapped[LeadLostReason | None] = mapped_column(
        Enum(LeadLostReason, name="lead_lost_reason"),
        nullable=True,
    )

    lost_reason_notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    qualification_notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    enquiry = relationship("Enquiry", back_populates="lead")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    assigned_account = relationship("Account", foreign_keys=[assigned_account_id])
    