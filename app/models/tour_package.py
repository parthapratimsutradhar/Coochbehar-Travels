import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TourType
from app.models.base import ActiveEntity


class TourPackage(ActiveEntity):
    __tablename__ = "tour_packages"

    tour_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    type: Mapped[TourType] = mapped_column(
        Enum(
            TourType,
            native_enum=False,
            validate_strings=True,
            length=20,
        ),
        default=TourType.DOMESTIC,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

# ── Relationships ───────────────────────────────────────────────────────
    variants = relationship(
        "TourVariant",
        back_populates="package",
        cascade="all, delete-orphan",
    )

    reviews = relationship(
        "Review",
        back_populates="tour_package",
        cascade="all, delete-orphan",
    )

    enquiries = relationship(
        "Enquiry",
        back_populates="package",
    )
    
    wishlists = relationship(
        "TourWishlist",
        back_populates="package",
        cascade="all, delete-orphan",
    )
    
    quotations = relationship(
        "Quotation", 
        back_populates="package"
    )
    
    destination = relationship(
        "Destination",
        foreign_keys=[destination_id],
        back_populates="tour_packages",
    )