import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class ReferralRewardConfig(BaseEntity):
    """Admin-configurable default referral reward settings."""

    __tablename__ = "referral_reward_configs"

    default_reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    
    booking_window_days: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
    )
    
    updated_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

# ── Relationships ───────────────────────────────────────────────────────

    updated_by = relationship(
        "Account",
        foreign_keys=[updated_by_account_id],
        back_populates="updated_referral_config",
    )
    
