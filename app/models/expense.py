
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import ARRAY, UUID, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ActiveEntity


class Expense(ActiveEntity):
    __tablename__ = "expenses"

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )       
    
    expense_category: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    payment_method: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    
    attachments: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(1000)),
        nullable=True,
    )

    created_by_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )