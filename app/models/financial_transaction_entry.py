import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.financial_account import FinancialAccount
    from app.models.financial_transaction import FinancialTransaction


class FinancialTransactionEntry(BaseEntity):
    __tablename__ = "financial_transaction_entries"
    __table_args__ = (
        CheckConstraint(
            "debit >= 0", 
            name="ck_financial_entry_debit_nonnegative"
        ),
        
        CheckConstraint(
            "credit >= 0", 
            name="ck_financial_entry_credit_nonnegative"
        ),
        
        CheckConstraint(
            "NOT (debit > 0 AND credit > 0)",
            name="ck_financial_entry_debit_or_credit",
        ),
        
        CheckConstraint(
            "debit > 0 OR credit > 0",
            name="ck_financial_entry_nonzero",
        ),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    debit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    credit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0
    )

    description: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True
    )

    transaction: Mapped["FinancialTransaction"] = relationship(
        "FinancialTransaction", back_populates="entries"
    )
    account: Mapped["FinancialAccount"] = relationship(
        "FinancialAccount", back_populates="entries"
    )
