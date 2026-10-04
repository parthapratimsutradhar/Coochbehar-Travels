from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TourType
from app.models.base import UUIDEntity


class TourPointConfigurationHistory(UUIDEntity):
    __tablename__ = "tour_point_configuration_history"

    configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_point_configurations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tour_type: Mapped[TourType] = mapped_column(
        Enum(TourType, native_enum=False, validate_strings=True, length=20), nullable=False, index=True
    )
    previous_amount_per_point: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_per_point: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    changed_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    changed_by_account = relationship("Account", foreign_keys=[changed_by_account_id])
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )