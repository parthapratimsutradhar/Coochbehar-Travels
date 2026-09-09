import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PaymentMethod, PaymentStatus, TransactionType
from app.models.booking import Booking
from app.models.account import Account
from app.models.base import UUIDEntity


class BookingPayment(UUIDEntity):
    """
    Payment transaction associated with a booking.

    Supports advance payments, installments, full payments,
    refunds and offline/manual payments.
    """

    __tablename__ = "booking_payments"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_booking_payment_amount_positive",
        ),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
    )

    transaction_type:  Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type",
        ),
        nullable=False,
        default=TransactionType.PAYMENT,
        index=True,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            name="payment_method",
        ),
        nullable=False,
        default=PaymentMethod.RAZORPAY,
        index=True,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status",
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )

    gateway: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    gateway_order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    gateway_signature: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recorded_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    booking: Mapped["Booking"] = relationship(
        "Booking",
        back_populates="payments",
    )

    recorded_by: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[recorded_by_account_id],
        back_populates="payments_recorded",
    )
