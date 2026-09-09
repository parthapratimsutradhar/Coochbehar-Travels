from sqlalchemy import Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ActiveEntity
from decimal import Decimal

from app.core.enums import VehicleType

class Vehicle(ActiveEntity):
    __tablename__ = "vehicles"

    name: Mapped[str] = mapped_column(
        String(100),
    )
    
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType),
        nullable=False,
        index=True,
        default=VehicleType.ANY,
    )

    registration_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
    )

    capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    price_per_day: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )
