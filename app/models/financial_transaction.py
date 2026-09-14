import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    FinancialTransactionStatus,
    FinancialTransactionType,
    PaymentMethod,
)
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.financial_transaction_entry import FinancialTransactionEntry


class FinancialTransaction(BaseEntity):
    __tablename__ = "financial_transactions"
    __table_args__ = (
        Index("ix_financial_transactions_transaction_date", "transaction_date"),
        Index("ix_financial_transactions_external_reference", "external_reference"),
    )

    transaction_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    transaction_type: Mapped[FinancialTransactionType] = mapped_column(
        Enum(FinancialTransactionType, name="financial_transaction_type"),
        nullable=False,
        index=True,
    )
    status: Mapped[FinancialTransactionStatus] = mapped_column(
        Enum(FinancialTransactionStatus, name="financial_transaction_status"),
        nullable=False,
        default=FinancialTransactionStatus.POSTED,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enquiries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method", create_type=False), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    entries: Mapped[list["FinancialTransactionEntry"]] = relationship(
        "FinancialTransactionEntry",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="FinancialTransactionEntry.created_at",
    )
