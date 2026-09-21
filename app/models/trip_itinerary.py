from datetime import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity
from app.core.enums import MealPlan

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.quotation import Quotation

class TripItinerary(BaseEntity):
    __tablename__ = "trip_itinerary"
    
    __table_args__ = (
        UniqueConstraint(
            "quotation_id",
            "day_number",
            name="uq_quotation_itinerary_day",
        ),
        UniqueConstraint(
            "booking_id",
            "day_number",
            name="uq_booking_itinerary_day",
        ),
        CheckConstraint(
            "day_number > 0",
            name="ck_trip_itinerary_day_positive",
        ),
        CheckConstraint(
            "(quotation_id IS NOT NULL) <> (booking_id IS NOT NULL)",
            name="ck_trip_itinerary_single_owner",
        ),
    )

    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    day_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    overnight_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    meal_plan: Mapped[MealPlan | None] = mapped_column(
        Enum(MealPlan, name="meal_plan"),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

# ── Relationships ───────────────────────────────────────────────────────    

    quotation: Mapped["Quotation | None"] = relationship(
        back_populates="itinerary",
    )

    booking: Mapped["Booking | None"] = relationship(
        back_populates="trip_itinerary",
    )
