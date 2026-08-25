import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import ReferralStatus
from app.models.base import UUIDEntity


class Referral(UUIDEntity):
    """
    Tracks a customer referral relationship.

    A customer can refer another customer using a referral code.
    The referral remains independent from the authentication system.
    """
    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint(
            "referrer_customer_id <> referred_customer_id",
            name="ck_referral_no_self_referral",
        ),
    )

    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    referred_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    referral_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[ReferralStatus] = mapped_column(
        Enum(
            ReferralStatus,
            name="referral_status",
        ),
        nullable=False,
        default=ReferralStatus.PENDING,
        index=True,
    )

    reward_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    reward_issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

# ── Relationships ──────────────────────────────────────────────

    referrer = relationship(
        "Customer",
        foreign_keys=[referrer_customer_id],
        back_populates="referrals_made",
    )

    referred_customer = relationship(
        "Customer",
        foreign_keys=[referred_customer_id],
        back_populates="referral_received",
    )
    