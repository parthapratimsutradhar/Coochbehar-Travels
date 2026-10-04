import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PointTransactionType
from app.models.base import UUIDEntity


class TourPointTransaction(UUIDEntity):
    __tablename__ = "tour_point_transactions"
    __table_args__ = (
        UniqueConstraint("booking_id", "transaction_type", name="uq_tour_point_booking_event"),
        Index("ix_tour_point_transactions_account_created", "account_id", "created_at"),
        Index("ix_tour_point_transactions_created_at", "created_at"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_point_configurations.id", ondelete="SET NULL"), nullable=True
    )
    transaction_type: Mapped[PointTransactionType] = mapped_column(
        Enum(PointTransactionType, native_enum=False, validate_strings=True, length=30), nullable=False
    )
    points: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    amount_per_point: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    booking_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tour_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    account = relationship("Account")
    booking = relationship("Booking")
    package = relationship("TourPackage")
