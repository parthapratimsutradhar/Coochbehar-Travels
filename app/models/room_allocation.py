import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDEntity


class RoomAllocation(UUIDEntity):
    __tablename__ = "room_allocations"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    room_number: Mapped[str | None] = mapped_column(String(30))
    room_type: Mapped[str | None] = mapped_column(String(50))
    occupant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    booking = relationship("Booking")
    room = relationship("Room")
