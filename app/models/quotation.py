from tokenize import Number
import uuid

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import QuotationStatus
from app.models.account import Account
from app.models.base import BaseEntity
from app.models.enquiry import Enquiry
from app.models.quotation_item import QuotationItem
from app.models.tour_package import TourPackage
from app.models.tour_variant import TourVariant


class Quotation(BaseEntity):
    """
    Commercial quotation generated for an enquiry.

    Each quotation record represents one commercial version of the
    quotation for that enquiry.

    Example:

        ENQ-1001
            ├── QT-1001-V1
            ├── QT-1001-V2
            └── QT-1001-V3  <- Accepted

    A quotation is separate from the final booking.
    """

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
            "adult_count >= 0",
            name="ck_quotation_adult_count_non_negative",
        ),
        CheckConstraint(
            "child_count >= 0",
            name="ck_quotation_child_count_non_negative",
        ),
        CheckConstraint(
            "senior_count >= 0",
            name="ck_quotation_senior_count_non_negative",
        ),
        CheckConstraint(
            "adult_count + child_count + senior_count > 0",
            name="ck_quotation_has_traveller",
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

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enquiries.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tour_packages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tour_variants.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tour_offers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    tour_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    destination: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "destinations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    travel_date: Mapped[Date | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    return_date: Mapped[Date | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    adult_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    child_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    senior_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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
    
    room_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    
    vehicle: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    meal_plan: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    status: Mapped[QuotationStatus] = mapped_column(
        Enum(
            QuotationStatus,
            name="quotation_status",
        ),
        nullable=False,
        default=QuotationStatus.DRAFT,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    terms_and_conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "accounts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
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

# ── Relationships ───────────────────────────────────────────────────────

    customer: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[customer_id],
        back_populates="quotations",
    )

    enquiry: Mapped["Enquiry | None"] = relationship(
        "Enquiry",
        back_populates="quotations",
    )

    package: Mapped["TourPackage | None"] = relationship(
        "TourPackage",
        back_populates="quotations",
    )

    variant: Mapped["TourVariant | None"] = relationship(
        "TourVariant",
        back_populates="quotations",
    )

    offer = relationship(
        "TourOffer",
        foreign_keys=[offer_id],
        back_populates="quotations",
    )

    offer_usages = relationship(
        "TourOfferUsage",
        back_populates="quotation",
        cascade="all, delete-orphan",
    )

    destination_ref = relationship(
        "Destination",
        foreign_keys=[destination_id],
        back_populates="quotations",
    )

    created_by: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[created_by_account_id],
    )

    items: Mapped[list["QuotationItem"]] = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationItem.created_at",
    )