
from datetime import date
import uuid

from app.models.base import ActiveEntity

from decimal import Decimal
from sqlalchemy import Date, ForeignKey, Integer, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column
    
class TourDeparture(ActiveEntity):
    __tablename__ = "tour_departures"
    __table_args__ = (
        CheckConstraint("total_seats >= 0", name="ck_departure_total_seats_non_negative"),
        CheckConstraint(
            "available_seats >= 0 AND available_seats <= total_seats",
            name="ck_departure_available_seats_valid",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tour_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    departure_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    return_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    total_seats: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    available_seats: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

# ── Relationships ───────────────────────────────────────────────────────

    variant = relationship(
        "TourVariant",
        back_populates="departures"
    )
    
    bookings = relationship(
        "Booking", 
        back_populates="departure"
    )