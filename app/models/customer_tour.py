import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CustomerTourStatus
from app.models.base import BaseEntity


class CustomerTour(BaseEntity):
    """
    Stores a customer's previous, current, or planned tour.

    A tour may originate from:
    - a fixed/catalog tour
    - a custom tour enquiry
    - an offline/manual entry

    Catalog references are optional so custom tours can be tracked
    without requiring a package or variant.
    """

    __tablename__ = "customer_tours"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional: present for fixed/catalog tours
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Optional: present for fixed/catalog tours
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Optional: identifies the enquiry/request that created this tour record
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    tour_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    destination: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    travel_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    return_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    pax_no: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    status: Mapped[CustomerTourStatus] = mapped_column(
        Enum(
            CustomerTourStatus,
            name="customer_tour_status",
        ),
        nullable=False,
        default=CustomerTourStatus.PLANNED,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    customer = relationship(
        "Customer",
        back_populates="tours",
    )

    package = relationship(
        "TourPackage",
    )

    variant = relationship(
        "TourVariant",
    )

    enquiry = relationship(
        "Enquiry",
        back_populates="customer_tour",
    )

    created_by = relationship(
        "User",
    )