# app/models/tour_route_stop.py

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TourRouteStop(Base):
    __tablename__ = "tour_route_stops"

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

    location: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    nights: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    tour_package = relationship(
        "TourPackage",
        back_populates="route_stops",
    )