
from sqlalchemy import  Integer, String, Text, Numeric
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ActiveEntity


class Room(ActiveEntity):
    __tablename__ = "rooms"

    room_code: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    room_number: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
    )

    room_type: Mapped[str | None] = mapped_column(
        String(50),
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
