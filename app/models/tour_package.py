# app/models/tour_package.py

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TourPackage(Base):
    __tablename__ = "tour_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    duration_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    duration_nights: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    season: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    departures = relationship(
        "TourDeparture",
        back_populates="tour_package",
        cascade="all, delete-orphan",
        order_by="TourDeparture.departure_date",
    )

    route_stops = relationship(
        "TourRouteStop",
        back_populates="tour_package",
        cascade="all, delete-orphan",
        order_by="TourRouteStop.sort_order",
    )

    highlights = relationship(
        "TourHighlight",
        back_populates="tour_package",
        cascade="all, delete-orphan",
        order_by="TourHighlight.sort_order",
    )

    gallery = relationship(
        "TourGallery",
        back_populates="tour_package",
        cascade="all, delete-orphan",
        order_by="TourGallery.sort_order",
    )

    itinerary = relationship(
        "TourItineraryDay",
        back_populates="tour_package",
        cascade="all, delete-orphan",
        order_by="TourItineraryDay.day_number",
    )

    reviews = relationship(
        "Review",
        back_populates="tour_package",
        cascade="all, delete-orphan",
    )