import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity
from app.core.enums import QuotationStatus


class Quotation(BaseEntity):
    __tablename__ = "quotations"
    
    __table_args__ = (
        UniqueConstraint(
            "enquiry_id",
            "version",
            name="uq_quotation_enquiry_version",
        ),
        CheckConstraint(
            "version > 0",
            name="ck_quotation_version_positive",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_quotation_subtotal_non_negative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_quotation_discount_non_negative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="ck_quotation_tax_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_quotation_total_non_negative",
        ),
    )

    quotation_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    enquiry_id: Mapped[uuid.UUID ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tour_packages.id", ondelete="SET NULL"),
        nullable=True,
    )

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tour_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
    )

    tour_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    travel_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    return_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[QuotationStatus] = mapped_column(
        Enum(QuotationStatus, name="quotation_status"),
        nullable=False,
    )

    terms_and_conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    important_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    inclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    exclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rejected_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────

    customer = relationship(
        "Account",
        foreign_keys=[customer_id],
        back_populates="quotations",
    )

    enquiry = relationship(
        "Enquiry",
        back_populates="quotations",
    )

    items: Mapped[list["TripItem"]] = relationship(
        "TripItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="TripItem.sort_order",
    )

    itinerary: Mapped[list["TripItinerary"]] = relationship(
        "TripItinerary",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="TripItinerary.day_number",
    )

    bookings = relationship(
        "Booking",
        back_populates="quotation",
    )

    offer_usages = relationship(
        "TourOfferUsage",
        back_populates="quotation",
    )