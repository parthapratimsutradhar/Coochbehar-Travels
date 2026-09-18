import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import LeadChannel, LeadActivityType
from app.models.base import BaseEntity


class LeadActivity(BaseEntity):
    __tablename__ = "lead_activities"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel: Mapped[LeadChannel] = mapped_column(
        Enum(LeadChannel, name="lead_channel"),
        nullable=False,
    )

    activity_type: Mapped[LeadActivityType] = mapped_column(
        Enum(LeadActivityType, name="lead_activity_type"),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    lead = relationship("Lead", back_populates="activities")
    account = relationship("Account", back_populates="lead_activities")
