import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class TourOfferUsage(BaseEntity):
    __tablename__ = "tour_offer_usages"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tour_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )
    
# ── Relationships ───────────────────────────────────────────────────────

    offer = relationship(
        "TourOffer",
        back_populates="usages",
    )

    customer = relationship(
        "Account",
        foreign_keys=[customer_id],
        back_populates="offer_usages",
    )

    booking = relationship(
        "Booking",
        foreign_keys=[booking_id],
        back_populates="offer_usages",
    )

    quotation = relationship(
        "Quotation",
        foreign_keys=[quotation_id],
        back_populates="offer_usages",
    )
