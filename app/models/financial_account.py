import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FinancialAccountOwnerType, FinancialAccountType
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.financial_transaction_entry import FinancialTransactionEntry


class FinancialAccount(BaseEntity):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint("account_code", name="uq_financial_accounts_account_code"),
        UniqueConstraint(
            "owner_type",
            "owner_id",
            "account_type",
            name="uq_financial_accounts_owner_type_id_type",
        ),
    )

    account_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[FinancialAccountType] = mapped_column(
        Enum(FinancialAccountType, name="financial_account_type"),
        nullable=False,
        index=True,
    )
    owner_type: Mapped[FinancialAccountOwnerType] = mapped_column(
        Enum(FinancialAccountOwnerType, name="financial_account_owner_type"),
        nullable=False,
        default=FinancialAccountOwnerType.SYSTEM,
        index=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    entries: Mapped[list["FinancialTransactionEntry"]] = relationship(
        "FinancialTransactionEntry", back_populates="account"
    )
