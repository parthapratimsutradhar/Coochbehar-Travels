from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.schemas.base import SchemaBase


class ExpenseBase(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    description: str | None = Field(default=None, max_length=255)
    date: datetime | None = None
    expense_category: str = Field(..., min_length=1, max_length=100)
    payment_method: str = Field(..., min_length=1, max_length=100)
    vendor_id: UUID | None = None
    financial_account_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=255)
    attachments: list[str] | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(SchemaBase):
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=255)
    date: datetime | None = None
    expense_category: str | None = Field(default=None, min_length=1, max_length=100)
    payment_method: str | None = Field(default=None, min_length=1, max_length=100)
    vendor_id: UUID | None = None
    financial_account_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=255)
    attachments: list[str] | None = None
    is_active: bool | None = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by_account_id: UUID
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


def expense_response(transaction) -> ExpenseResponse:
    metadata = transaction.metadata_ or {}
    return ExpenseResponse.model_validate(
        {
            "id": transaction.id,
            "amount": transaction.amount,
            "description": transaction.description,
            "date": transaction.transaction_date,
            "expense_category": transaction.category,
            "payment_method": (
                transaction.payment_method.value
                if transaction.payment_method is not None
                else "OTHER"
            ),
            "vendor_id": transaction.vendor_id,
            "financial_account_id": transaction.metadata_.get("financial_account_id") if transaction.metadata_ else None,
            "reference": transaction.reference,
            "attachments": metadata.get("attachments"),
            "created_by_account_id": transaction.created_by_account_id,
            "is_active": transaction.status not in {"CANCELLED", "REVERSED"},
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
        }
    )
