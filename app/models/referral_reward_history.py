import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class ReferralRewardHistory(BaseEntity):
    __tablename__ = "referral_reward_history"

    referral_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    approved_reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    credit_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    approved_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

# ── Relationships ───────────────────────────────────────────────────────

    referral = relationship("Referral", back_populates="reward_history")
    
    approved_by = relationship(
        "Account",
        foreign_keys=[approved_by_account_id],
        back_populates="approved_referral_rewards",
    )
