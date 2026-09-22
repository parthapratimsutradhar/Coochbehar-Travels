from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.enums import PaymentMethod
from app.schemas.base import SchemaBase


class VendorPaymentCreate(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    vendor_id: UUID
    booking_id: UUID | None = None
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: str | None = Field(default=None, max_length=255)
    description: str | None = None
    paid_at: datetime | None = None


class FinancialReversalCreate(SchemaBase):
    reason: str = Field(..., min_length=1, max_length=500)
