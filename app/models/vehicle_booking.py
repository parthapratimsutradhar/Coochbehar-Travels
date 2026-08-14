import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VehicleBooking(Base):
    __tablename__ = "vehicle_bookings"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "bookings.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id"),
    )

    start_date: Mapped[date] = mapped_column(Date)

    end_date: Mapped[date] = mapped_column(Date)

    adults: Mapped[int]

    children: Mapped[int]

    booking = relationship("Booking")

    vehicle = relationship(
        "Vehicle",
        back_populates="bookings",
    )