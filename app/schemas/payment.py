from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.core.enums import PaymentMethod, PaymentStatus, TransactionType
from app.schemas.base import SchemaBase


class BookingPaymentCreate(SchemaBase):
    booking_id: UUID | None = None
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    payment_method: PaymentMethod = PaymentMethod.CASH
    transaction_type: TransactionType = TransactionType.PAYMENT
    status: PaymentStatus = PaymentStatus.SUCCESS
    gateway: str | None = None
    transaction_id: str | None = None
    notes: str | None = None
    paid_at: datetime | None = None


class BookingPaymentResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    amount: Decimal
    currency: str
    transaction_type: TransactionType
    payment_method: PaymentMethod
    status: PaymentStatus
    gateway: str | None
    transaction_id: str | None
    gateway_order_id: str | None
    gateway_payment_id: str | None
    paid_at: datetime | None
    refunded_at: datetime | None
    notes: str | None
    recorded_by_account_id: UUID | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
