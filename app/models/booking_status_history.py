import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BookingStatus
from app.models.base import UUIDEntity


class BookingStatusHistory(UUIDEntity):
    __tablename__ = "booking_status_history"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    
    previous_status: Mapped[BookingStatus | None] = mapped_column(
        Enum(BookingStatus, 
        name="booking_status"),
        nullable=True
    )
    
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), 
        nullable=False
    )
    
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    notes: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), 
        nullable=False
    )

# ── Relationships ───────────────────────────────────────────────────────

    booking = relationship(
        "Booking",
        back_populates="status_history"
    )
    changed_by = relationship("Account")
