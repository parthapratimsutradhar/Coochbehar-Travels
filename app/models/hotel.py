
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any
from sqlalchemy.dialects.postgresql import JSONB

from app.core.enums import HotelCategory
from app.models.base import ActiveEntity


class Hotel(ActiveEntity):
    __tablename__ = "hotels"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    image: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[HotelCategory | None] = mapped_column(
        Enum(HotelCategory, name="hotel_category"),
        nullable=True,
        index=True,
    )
    
    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    contact: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    destination_ref = relationship(
        "Destination",
        foreign_keys=[destination_id],
        back_populates="hotels",
    )

    enquiries = relationship(
        "Enquiry",
        back_populates="hotel",
    )
