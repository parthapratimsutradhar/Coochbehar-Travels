import uuid

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    vehicle_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
    )

    registration_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
    )

    capacity: Mapped[int] = mapped_column(
        Integer,
    )

    price_per_day: Mapped[float] = mapped_column(
        Numeric(10,2),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    bookings = relationship(
        "VehicleBooking",
        back_populates="vehicle",
    )