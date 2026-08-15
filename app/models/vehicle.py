import uuid
from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import ActiveEntity


class Vehicle(ActiveEntity):
    __tablename__ = "vehicles"

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

