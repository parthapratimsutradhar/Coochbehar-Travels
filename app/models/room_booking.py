import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RoomBooking(Base):
    __tablename__ = "room_bookings"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "bookings.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    
    room_booking_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id"),
    )

    check_in: Mapped[date] = mapped_column(Date)

    check_out: Mapped[date] = mapped_column(Date)

    adults: Mapped[int]

    children: Mapped[int]

    booking = relationship("Booking")

    room = relationship(
        "Room",
        back_populates="bookings",
    )