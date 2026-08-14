import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.core.enums import MealPlan, VehicleType


class CustomTourRequest(Base):
    __tablename__ = "custom_tour_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    request_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    visitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(100))

    mobile: Mapped[str] = mapped_column(String(20))

    destination: Mapped[str] = mapped_column(String(150))

    travel_date: Mapped[date | None] = mapped_column(Date)
    
    travel_duration: Mapped[str | None] = mapped_column(String(50))

    pax_no: Mapped[int] = mapped_column(
        Integer,
        default=4,
    )

    no_room: Mapped[int] = mapped_column(
        Integer,
        default=2,
    )
    
    vehicle_type: Mapped[VehicleType | None] = mapped_column(
        String(50),
        default=VehicleType.SIX_SEATER,
    )

    meal_plan: Mapped[MealPlan | None] = mapped_column(
        String(50),
        default=MealPlan.MAP,
    )

    special_requirements: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(30),
        default="NEW",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )