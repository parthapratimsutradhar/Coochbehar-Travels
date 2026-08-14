import uuid

from sqlalchemy import Boolean
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class TourVariant(Base, TimestampMixin):
    __tablename__ = "tour_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "tour_packages.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    variant_code: Mapped[str] = mapped_column(
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

    valid_from: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[Date] = mapped_column(
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

    base_price: Mapped[float] = mapped_column(
        Numeric(10,2),
        nullable=False,
    )

    seats: Mapped[int | None] = mapped_column(
        Integer,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

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