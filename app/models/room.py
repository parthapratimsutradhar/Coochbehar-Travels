import uuid

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    room_code = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    room_number = mapped_column(
        String(20),
        unique=True,
    )

    room_type = mapped_column(
        String(50),
    )

    capacity = mapped_column(
        Integer,
    )

    price_per_night = mapped_column(
        Numeric(10,2),
    )

    description = mapped_column(Text)

    is_active = mapped_column(
        Boolean,
        default=True,
    )

    bookings = relationship(
        "RoomBooking",
        back_populates="room",
    )