"""add wallet controls and financial integrity checks

Revision ID: 6b7c8d9e0f1a
Revises: 5a1ee1eb2633
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b7c8d9e0f1a"
down_revision: Union[str, Sequence[str], None] = "5a1ee1eb2633"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'WALLET'")
    op.create_check_constraint(
        "ck_financial_transactions_amount_positive",
        "financial_transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_booking_cost_estimated_nonnegative",
        "booking_costs",
        "estimated_amount >= 0",
    )
    op.create_check_constraint(
        "ck_booking_cost_actual_nonnegative",
        "booking_costs",
        "actual_amount >= 0",
    )
    op.create_check_constraint(
        "ck_booking_cost_paid_nonnegative",
        "booking_costs",
        "paid_amount >= 0",
    )
    op.create_check_constraint(
        "ck_booking_cost_due_nonnegative",
        "booking_costs",
        "due_amount >= 0",
    )
    op.create_check_constraint(
        "ck_booking_cost_paid_not_over_actual",
        "booking_costs",
        "paid_amount <= actual_amount",
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO financial_accounts
            (id, account_code, name, account_type, owner_type, owner_id, currency, is_active)
        SELECT gen_random_uuid(),
               'WALLET-' || substr(replace(a.id::text, '-', ''), 1, 23),
               a.name || ' Wallet', 'LIABILITY', 'CUSTOMER', a.id, 'INR', true
        FROM accounts a
        WHERE a.role = 'CUSTOMER'
          AND NOT EXISTS (
              SELECT 1 FROM financial_accounts fa
              WHERE fa.owner_type = 'CUSTOMER'
                AND fa.owner_id = a.id
                AND fa.account_type = 'LIABILITY'
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM financial_accounts
        WHERE owner_type = 'CUSTOMER'
          AND account_code LIKE 'WALLET-%'
          AND NOT EXISTS (
              SELECT 1 FROM financial_transaction_entries e
              WHERE e.account_id = financial_accounts.id
          )
        """
    )
    op.drop_constraint("ck_booking_cost_paid_not_over_actual", "booking_costs", type_="check")
    op.drop_constraint("ck_booking_cost_due_nonnegative", "booking_costs", type_="check")
    op.drop_constraint("ck_booking_cost_paid_nonnegative", "booking_costs", type_="check")
    op.drop_constraint("ck_booking_cost_actual_nonnegative", "booking_costs", type_="check")
    op.drop_constraint("ck_booking_cost_estimated_nonnegative", "booking_costs", type_="check")
    op.drop_constraint("ck_financial_transactions_amount_positive", "financial_transactions", type_="check")
