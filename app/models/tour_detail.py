import uuid
from typing import Any
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from app.models.base import UUIDEntity


class TourDetail(UUIDEntity):
    __tablename__ = "tour_details"

    variant_id: Mapped[uuid.UUID] = mapped_column(
            ForeignKey(
                "tour_variants.id",
                ondelete="CASCADE",
            ),
            unique=True,
            nullable=False,
            index=True,
    )
        
    banner: Mapped[str | dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    gallery: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    highlights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    inclusions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    exclusions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    departures_dates: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )  
    
    itinerary: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    route_stops: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )  

# ── Relationships ───────────────────────────────────────────────────────
    variant = relationship(
        "TourVariant",
        back_populates="details",
    )