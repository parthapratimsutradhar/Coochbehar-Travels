import uuid
from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Numeric
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any
from sqlalchemy.dialects.postgresql import JSONB

from app.core.enums import RoomType
from app.models.base import ActiveEntity


class Room(ActiveEntity):
    __tablename__ = "rooms"
    
    hotel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    room_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
    )

    room_image: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    room_type: Mapped[RoomType | None] = mapped_column(
        Enum(RoomType, name="room_type"),
        nullable=True,
        index=True,
    )

    capacity: Mapped[int | None] = mapped_column(
        Integer,
    )

    price_per_night: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text)

