from decimal import Decimal

import uuid
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDEntity

class BookingCost(UUIDEntity):
    """
    Represents the costs associated with a booking.
    Contains details about the various costs involved in the booking process.
    """
    __tablename__ = "booking_costs"
    __table_args__ = (
        CheckConstraint("estimated_amount >= 0", name="ck_booking_cost_estimated_nonnegative"),
        CheckConstraint("actual_amount >= 0", name="ck_booking_cost_actual_nonnegative"),
        CheckConstraint("paid_amount >= 0", name="ck_booking_cost_paid_nonnegative"),
        CheckConstraint("due_amount >= 0", name="ck_booking_cost_due_nonnegative"),
        CheckConstraint("paid_amount <= actual_amount", name="ck_booking_cost_paid_not_over_actual"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    cost_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    estimated_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    actual_amount: Mapped[Decimal] = mapped_column(
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
    
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )