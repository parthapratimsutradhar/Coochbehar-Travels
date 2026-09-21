import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity
from app.core.enums import RoomType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.trip_items import TripItem


class TripHotel(BaseEntity):
    __tablename__ = "trip_hotels"
    
    __table_args__ = (
        CheckConstraint(
            "check_out > check_in",
            name="ck_trip_hotel_checkout_after_checkin",
        ),
        CheckConstraint(
            "nights > 0",
            name="ck_trip_hotel_nights_positive",
        ),
        CheckConstraint(
            "room_count > 0",
            name="ck_trip_hotel_room_count_positive",
        ),
    )

    trip_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trip_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    hotel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    hotel_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    check_in: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    check_out: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    nights: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    room_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    room_type: Mapped[RoomType | None] = mapped_column(
        Enum(RoomType, name="room_type"),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────    

    trip_item: Mapped["TripItem"] = relationship(
        back_populates="hotel",
    )

