"""add financial ledger foundation

Revision ID: 9f4a1b2c3d4e
Revises: 43e002b7fd74
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9f4a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "43e002b7fd74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    account_type = postgresql.ENUM(
        "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE",
        name="financial_account_type", create_type=False,
    )
    owner_type = postgresql.ENUM(
        "SYSTEM", "CUSTOMER", "VENDOR",
        name="financial_account_owner_type", create_type=False,
    )
    transaction_type = postgresql.ENUM(
        "BOOKING_PAYMENT", "BOOKING_REFUND", "WALLET_CREDIT", "WALLET_DEBIT",
        "EXPENSE", "VENDOR_PAYMENT", "TRANSFER", "ADJUSTMENT", "REFERRAL_REWARD",
        name="financial_transaction_type", create_type=False,
    )
    transaction_status = postgresql.ENUM(
        "PENDING", "POSTED", "FAILED", "CANCELLED", "REVERSED",
        name="financial_transaction_status", create_type=False,
    )
    for enum in (account_type, owner_type, transaction_type, transaction_status):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "financial_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("account_code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("owner_type", owner_type, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("account_code", name="uq_financial_accounts_account_code"),
        sa.UniqueConstraint("owner_type", "owner_id", "account_type", name="uq_financial_accounts_owner_type_id_type"),
    )
    op.create_table(
        "financial_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("transaction_code", sa.String(40), nullable=False, unique=True),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("status", transaction_status, nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL")),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="SET NULL")),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotations.id", ondelete="SET NULL")),
        sa.Column("enquiry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("enquiries.id", ondelete="SET NULL")),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("payment_method", postgresql.ENUM(name="payment_method", create_type=False)),
        sa.Column("category", sa.String(100)),
        sa.Column("reference", sa.String(255)),
        sa.Column("external_reference", sa.String(255), unique=True),
        sa.Column("gateway", sa.String(50)),
        sa.Column("gateway_transaction_id", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("metadata", sa.JSON()),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="SET NULL")),
    )
    op.create_table(
        "financial_transaction_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("debit", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.String(255)),
        sa.CheckConstraint("debit >= 0", name="ck_financial_entry_debit_nonnegative"),
        sa.CheckConstraint("credit >= 0", name="ck_financial_entry_credit_nonnegative"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_financial_entry_debit_or_credit"),
        sa.CheckConstraint("debit > 0 OR credit > 0", name="ck_financial_entry_nonzero"),
    )


def downgrade() -> None:
    op.drop_table("financial_transaction_entries")
    op.drop_table("financial_transactions")
    op.drop_table("financial_accounts")
    for name in ("financial_transaction_status", "financial_transaction_type", "financial_account_owner_type", "financial_account_type"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
