from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.core.enums import (
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
    PaymentStatus,
    TransactionType,
)
from app.schemas.base import SchemaBase


class BookingPaymentCreate(SchemaBase):
    booking_id: UUID | None = None
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", max_length=10)
    payment_method: PaymentMethod = PaymentMethod.CASH
    transaction_type: FinancialTransactionType | TransactionType = FinancialTransactionType.INCOME
    status: FinancialTransactionStatus | PaymentStatus = FinancialTransactionStatus.COMPLETED
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
    transaction_type: FinancialTransactionType
    payment_method: PaymentMethod
    status: FinancialTransactionStatus
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


def payment_response(transaction) -> BookingPaymentResponse:
    return BookingPaymentResponse.model_validate(
        {
            "id": transaction.id,
            "booking_id": transaction.booking_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "transaction_type": transaction.transaction_type,
            "payment_method": transaction.payment_method,
            "status": transaction.status,
            "gateway": transaction.gateway,
            "transaction_id": transaction.gateway_transaction_id,
            "gateway_order_id": None,
            "gateway_payment_id": transaction.gateway_transaction_id,
            "paid_at": transaction.transaction_date,
            "refunded_at": None,
            "notes": transaction.description,
            "recorded_by_account_id": transaction.created_by_account_id,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
        }
    )
