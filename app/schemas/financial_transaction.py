from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import (
    FinancialExportFormat,
    FinancialPeriod,
    FinancialReportType,
    FinancialTransactionStatus,
    FinancialTransactionType,
    FinancialTransactionCategory,
    PaymentMethod,
)
from app.schemas.base import SchemaBase


class FinancialTransactionBase(SchemaBase):
    amount: Decimal = Field(..., gt=0)
    transaction_type: str | FinancialTransactionType = Field(
        ...,
        description="Type of financial transaction, such as income, expense, or referral income.",
    )
    category: str | FinancialTransactionCategory | None = Field(default=None, description="Category of the financial transaction.")
    description: str | None = Field(default=None, max_length=500)
    transaction_date: datetime | None = None
    status: FinancialTransactionStatus | None = Field(
        default=FinancialTransactionStatus.COMPLETED,
        description="Current processing state of the transaction.",
    )
    currency: str = Field(default="INR", min_length=3, max_length=3)
    payment_method: PaymentMethod | None = Field(default=None, description="Payment method used for the transaction.")
    vendor_id: UUID | None = None
    booking_id: UUID | None = None
    customer_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=255)


class FinancialTransactionCreate(FinancialTransactionBase):
    pass


class FinancialTransactionUpdate(SchemaBase):
    amount: Decimal | None = Field(default=None, gt=0)
    transaction_type: str | FinancialTransactionType | None = Field(default=None, description="Type of financial transaction.")
    category: str | FinancialTransactionCategory | None = Field(default=None, description="Category of the financial transaction.")
    description: str | None = Field(default=None, max_length=500)
    transaction_date: datetime | None = None
    status: FinancialTransactionStatus | None = Field(default=None, description="Current processing state.")
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    payment_method: PaymentMethod | None = Field(default=None, description="Payment method used.")
    vendor_id: UUID | None = None
    booking_id: UUID | None = None
    customer_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=255)


class FinancialReportDownloadRequest(SchemaBase):
    report_type: FinancialReportType = Field(
        default=FinancialReportType.INCOME,
        description="Financial report category to export.",
    )
    format: FinancialExportFormat = Field(
        default=FinancialExportFormat.CSV,
        description="Export format for the generated file.",
    )
    period: FinancialPeriod = Field(
        default=FinancialPeriod.MONTHLY,
        description="The date period the report should cover.",
    )
    start_date: date | None = Field(default=None, description="Inclusive start date for the report range.")
    end_date: date | None = Field(default=None, description="Inclusive end date for the report range.")


class FinancialTransactionResponse(FinancialTransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by_account_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    status: FinancialTransactionStatus


def financial_transaction_response(transaction) -> FinancialTransactionResponse:
    metadata = transaction.metadata_ or {}
    category_aliases = {
        FinancialTransactionCategory.BOOKING_PAYMENT: "booking_income",
        FinancialTransactionCategory.BOOKING_REFUND: "booking_refund",
        FinancialTransactionCategory.WALLET_CREDIT: "wallet_credit",
        FinancialTransactionCategory.WALLET_DEBIT: "wallet_debit",
        FinancialTransactionCategory.VENDOR_PAYMENT: "vendor_payment",
        FinancialTransactionCategory.TRANSFER: "transfer",
        FinancialTransactionCategory.ADJUSTMENT: "adjustment",
        FinancialTransactionCategory.REFERRAL_INCOME: "referral_income",
        FinancialTransactionCategory.REFERRAL_REWARD: "referral_reward",
    }
    category_value = transaction.category
    category = category_aliases.get(category_value, category_value.value if category_value else None)
    return FinancialTransactionResponse.model_validate(
        {
            "id": transaction.id,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type.value,
            "category": category,
            "description": transaction.description,
            "transaction_date": transaction.transaction_date,
            "status": transaction.status.value,
            "currency": transaction.currency,
            "payment_method": transaction.payment_method.value if transaction.payment_method else None,
            "vendor_id": transaction.vendor_id,
            "booking_id": transaction.booking_id,
            "customer_id": transaction.customer_id,
            "reference": transaction.reference,
            "created_by_account_id": transaction.created_by_account_id,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
        }
    )
