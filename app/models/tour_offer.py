import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OfferDiscountType, OfferStatus
from app.models.base import ActiveEntity


class TourOffer(ActiveEntity):
    """Offer/discount campaign applicable to tours."""

    __tablename__ = "tour_offers"
    
    __table_args__ = (
        CheckConstraint(
            "discount_value >= 0",
            name="ck_tour_offer_discount_value_non_negative",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_tour_offer_usage_limit_positive",
        ),
        CheckConstraint(
            "per_customer_limit IS NULL OR per_customer_limit > 0",
            name="ck_tour_offer_customer_limit_positive",
        ),
        CheckConstraint(
            "valid_until > valid_from",
            name="ck_tour_offer_valid_dates",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    status: Mapped[OfferStatus] = mapped_column(
        Enum(
            OfferStatus,
            name="offer_status",
        ),
        default=OfferStatus.DRAFT,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    discount_type: Mapped[OfferDiscountType] = mapped_column(
        Enum(
            OfferDiscountType,
            name="offer_discount_type",
        ),
        nullable=False,
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    min_booking_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    usage_limit: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    per_customer_limit: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    usage_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

# ── Relationships ───────────────────────────────────────────────────────

    package_links = relationship(
        "TourOfferPackage",
        back_populates="offer",
        cascade="all, delete-orphan",
    )

    usages = relationship(
        "TourOfferUsage",
        back_populates="offer",
        cascade="all, delete-orphan",
    )

    bookings = relationship(
        "Booking",
        back_populates="offer",
    )

    quotations = relationship(
        "Quotation",
        back_populates="offer",
    )

    @property
    def variant_ids(self) -> list[uuid.UUID]:
        return [link.variant_id for link in self.package_links]
