import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
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
        primary_key=True,
    )
    
    tour_detail_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )
    
    banner: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    gallery: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    highlights: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    inclusions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    exclusions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    departures_dates: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )  
    
    itinerary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    route_stops: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )  

    variant = relationship(
        "TourVariant",
        back_populates="details",
    )