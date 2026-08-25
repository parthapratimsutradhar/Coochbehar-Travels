import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CustomerTourStatus
from app.models.base import BaseEntity


class CustomerTour(BaseEntity):
    """
    Stores a customer's previous, current, or planned tour.

    Can reference an existing catalog tour package/variant, while also
    supporting manually entered offline tours that are not present
    in the catalog.
    """

    __tablename__ = "customer_tours"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_variants.id", ondelete="SET NULL"),
        nullable=True,
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

    # ── Relationships ─────────────────────────────────────────────

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

    created_by = relationship(
        "User",
    )