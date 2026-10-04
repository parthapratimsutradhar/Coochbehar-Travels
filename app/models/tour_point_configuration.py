import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import TourType
from app.models.base import BaseEntity


class TourPointConfiguration(BaseEntity):
    __tablename__ = "tour_point_configurations"
    __table_args__ = (UniqueConstraint("tour_type", name="uq_tour_point_configuration_type"),)

    tour_type: Mapped[TourType] = mapped_column(
        Enum(TourType, native_enum=False, validate_strings=True, length=20), nullable=False
    )
    amount_per_point: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    updated_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
