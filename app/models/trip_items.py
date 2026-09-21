import uuid

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.core.enums import CostItemType
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.trip_hotel import TripHotel
    from app.models.trip_vehicle import TripVehicle
    from app.models.quotation import Quotation

class TripItem(BaseEntity):
    __tablename__ = "trip_items"
    
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_trip_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_trip_item_unit_price_non_negative",
        ),
        CheckConstraint(
            "total_price >= 0",
            name="ck_trip_item_total_price_non_negative",
        ),
        CheckConstraint(
            "(quotation_id IS NOT NULL) <> (booking_id IS NOT NULL)",
            name="ck_trip_item_single_owner",
        ),
    )

    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    item_type: Mapped[CostItemType] = mapped_column(
        Enum(CostItemType, name="cost_item_type"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

# ── Relationships ───────────────────────────────────────────────────────    

    quotation: Mapped["Quotation | None"] = relationship(
        back_populates="items",
    )

    booking: Mapped["Booking"] = relationship(
        back_populates="trip_items",
    )

    hotel: Mapped["TripHotel | None"] = relationship(
        back_populates="trip_item",
        uselist=False,
        cascade="all, delete-orphan",
    )

    vehicle: Mapped["TripVehicle | None"] = relationship(
        back_populates="trip_item",
        uselist=False,
        cascade="all, delete-orphan",
    )

    