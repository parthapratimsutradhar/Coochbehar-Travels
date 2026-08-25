import uuid
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import ActiveEntity
from decimal import Decimal
from datetime import date


class TourVariant(ActiveEntity):
    __tablename__ = "tour_variants"

    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "tour_packages.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    season_name: Mapped[str | None] = mapped_column(
        String(100),
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date] = mapped_column(
        Date,
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

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    seats: Mapped[int | None] = mapped_column(
        Integer,
    )

    badge: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    availability: Mapped[str | None] = mapped_column(
        String(20),
        default="AVAILABLE",
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

# ── Relationships ───────────────────────────────────────────────────────
    package = relationship(
        "TourPackage",
        back_populates="variants",
    )

    details = relationship(
        "TourDetail",
        back_populates="variant",
        uselist=False,
        cascade="all, delete-orphan",
    )

    enquiries = relationship(
        "Enquiry",
        back_populates="variant",
    )
