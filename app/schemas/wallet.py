from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import FinancialTransactionStatus, PaymentMethod, PaymentStatus
from app.schemas.base import SchemaBase


class WalletTopUpCreate(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod = PaymentMethod.RAZORPAY
    status: PaymentStatus = PaymentStatus.PENDING
    gateway: str | None = Field(default=None, max_length=50)
    gateway_transaction_id: str | None = Field(default=None, max_length=255)
    external_reference: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class WalletPaymentCreate(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    description: str | None = None


class WalletAdjustmentCreate(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    direction: str = Field(..., pattern="^(CREDIT|DEBIT)$")
    reason: str = Field(..., min_length=1, max_length=500)
    reference: str | None = Field(default=None, max_length=255)


class WalletRefundCreate(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    booking_id: UUID | None = None
    reason: str = Field(..., min_length=1, max_length=500)
    reference: str = Field(..., min_length=1, max_length=255)


class WalletTransactionResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_code: str
    transaction_type: str
    status: FinancialTransactionStatus
    amount: Decimal
    currency: str
    payment_method: PaymentMethod | None
    external_reference: str | None
    gateway: str | None
    gateway_transaction_id: str | None
    description: str | None
    transaction_date: datetime


class WalletResponse(SchemaBase):
    account_id: UUID
    customer_id: UUID
    balance: Decimal
    currency: str
    transactions: list[WalletTransactionResponse] = Field(default_factory=list)
