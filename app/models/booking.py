from decimal import Decimal

import uuid
from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BookingSource, BookingStatus
from app.models.base import BaseEntity

class Booking(BaseEntity):
    """
    Represents a booking made by a customer for a tour package or variant.
    Contains details about the booking, including customer information,
    tour details, and booking status.
    """
    __tablename__ = "bookings"

    booking_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="SET NULL"),
        nullable=True,
    )

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_variants.id", ondelete="SET NULL"),
        nullable=True,
    )

    booking_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_offers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    source: Mapped[BookingSource] = mapped_column(
        Enum(BookingSource, name="booking_source"),
        nullable=False,
        index=True,
    )
    
    sales_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"),
        nullable=False,
        index=True,
    )
    
    departure_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_departures.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    adult_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    child_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    senior_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    due_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text)
    
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
# ── Relationships ───────────────────────────────────────────────────────
    
    customer = relationship(
        "Account",
        foreign_keys="Booking.customer_id",
        back_populates="bookings",
    )
        
    sales_account = relationship(
        "Account",
        foreign_keys=[sales_account_id],
        back_populates="sales_bookings",
    )

    created_by_account = relationship(
        "Account",
        foreign_keys=[created_by],
        back_populates="created_bookings",
    )

    travellers = relationship(
        "BookingTraveler",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
    
    departure = relationship(
        "TourDeparture",
        back_populates="bookings",
    )

    package = relationship("TourPackage")
    
    variant = relationship("TourVariant")
    
    enquiry = relationship(
        "Enquiry",
        back_populates="booking"
    )
    
    quotation = relationship("Quotation")
    
    offer = relationship(
        "TourOffer",
        foreign_keys=[offer_id],
        back_populates="bookings",
    )
    
    offer_usages = relationship(
        "TourOfferUsage",
        back_populates="booking",
        cascade="all, delete-orphan",
    )
    
    status_history = relationship(
        "BookingStatusHistory",
        back_populates="booking",
        cascade="all, delete-orphan",
    )