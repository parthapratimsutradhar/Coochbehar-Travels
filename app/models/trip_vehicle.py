
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity
from app.core.enums import VehicleType


class TripVehicle(BaseEntity):
    __tablename__ = "trip_vehicles"
    
    __table_args__ = (
            CheckConstraint(
                "end_date > start_date",
                name="ck_trip_vehicle_end_after_start",
            ),
            CheckConstraint(
                "days > 0",
                name="ck_trip_vehicle_days_positive",
            ),
            CheckConstraint(
                "quantity > 0",
                name="ck_trip_vehicle_quantity_positive",
            ),
        )

    trip_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trip_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    vehicle_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    vehicle_type: Mapped[VehicleType | None] = mapped_column(
        Enum(VehicleType, name="vehicle_type"),
        nullable=True,
    )

    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    rental_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

