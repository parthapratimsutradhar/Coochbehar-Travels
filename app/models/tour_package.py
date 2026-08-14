import string
import uuid

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TourType
from app.models.base import Base
from app.models.mixins import TimestampMixin


class TourPackage(Base, TimestampMixin):
    __tablename__ = "tour_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

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

    destination: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

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