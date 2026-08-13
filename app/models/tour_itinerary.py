# app/models/tour_itinerary.py

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TourItineraryDay(Base):
    __tablename__ = "tour_itinerary_days"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tour_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    tour_package = relationship(
        "TourPackage",
        back_populates="itinerary",
    )