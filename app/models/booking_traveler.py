
import uuid
from datetime import  date
from sqlalchemy import (
    Enum,
    ForeignKey,
    String,
    Date,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDEntity
from app.core.enums import Gender

class BookingTraveler(UUIDEntity):
    __tablename__ = "booking_travelers"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender"),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    relationship_to_customer: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
# ── Relationships ───────────────────────────────────────────────────────    

    booking = relationship(
        "Booking", 
        back_populates="travellers"
    )