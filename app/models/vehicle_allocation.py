

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey,  String, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDEntity


class VehicleAllocation(UUIDEntity):
    __tablename__ = "vehicle_allocations"

    booking_id : Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    vehicle_id : Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    vehicle_type : Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    vehicle_name : Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    registration_number : Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    start_date : Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date : Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    driver_name : Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    driver_mobile : Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    notes : Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )