"""use income and expense transaction types

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE financial_transactions "
        "ALTER COLUMN transaction_type TYPE VARCHAR(32) "
        "USING transaction_type::text"
    )
    op.execute(
        "UPDATE financial_transactions "
        "SET category = transaction_type::financial_transaction_category "
        "WHERE category IS NULL AND transaction_type IN ("
        "'BOOKING_PAYMENT', 'BOOKING_REFUND', 'WALLET_CREDIT', 'WALLET_DEBIT', "
        "'VENDOR_PAYMENT', 'TRANSFER', 'ADJUSTMENT', 'REFERRAL_REWARD', 'REFERRAL_INCOME'"
        ")"
    )
    op.execute(
        "UPDATE financial_transactions SET transaction_type = CASE "
        "WHEN transaction_type IN ("
        "'INCOME', 'BOOKING_PAYMENT', 'BOOKING_INCOME', 'WALLET_CREDIT', "
        "'TRANSFER', 'REFERRAL_INCOME', 'REFERRAL_REWARD'"
        ") THEN 'INCOME' "
        "WHEN transaction_type IN ("
        "'EXPENSE', 'BOOKING_REFUND', 'WALLET_DEBIT', 'VENDOR_PAYMENT', 'ADJUSTMENT'"
        ") THEN 'EXPENSE' "
        "ELSE transaction_type END"
    )
    op.execute("DROP TYPE financial_transaction_type")
    op.execute("CREATE TYPE financial_transaction_type AS ENUM ('INCOME', 'EXPENSE')")
    op.execute(
        "ALTER TABLE financial_transactions "
        "ALTER COLUMN transaction_type TYPE financial_transaction_type "
        "USING transaction_type::financial_transaction_type"
    )


def downgrade() -> None:
    raise NotImplementedError("Transaction type normalization cannot be reversed without losing category data.")