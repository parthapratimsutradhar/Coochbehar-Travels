"""migrate legacy finance rows and remove duplicate tables

Revision ID: a7b8c9d0e1f2
Revises: 9f4a1b2c3d4e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = ("9f4a1b2c3d4e", "c8d9e0f1a2b3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO financial_accounts
            (id, account_code, name, account_type, owner_type, currency, is_active)
        VALUES
            (gen_random_uuid(), '1000', 'Cash', 'ASSET', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '1010', 'Bank', 'ASSET', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '1020', 'Razorpay', 'ASSET', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '1100', 'Customer Receivable', 'ASSET', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '2000', 'Vendor Payable', 'LIABILITY', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '4000', 'Tour Revenue', 'REVENUE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5000', 'Hotel Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5010', 'Transport Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5020', 'Flight Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5030', 'Meal Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5040', 'Activity Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5050', 'Marketing Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '5060', 'Other Expense', 'EXPENSE', 'SYSTEM', 'INR', true),
            (gen_random_uuid(), '6000', 'Referral Reward Expense', 'EXPENSE', 'SYSTEM', 'INR', true)
        ON CONFLICT (account_code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO financial_transactions
            (id, created_at, updated_at, transaction_code, transaction_type, status,
             customer_id, booking_id, amount, currency, payment_method, gateway,
             gateway_transaction_id, description, transaction_date, created_by_account_id,
             external_reference)
        SELECT gen_random_uuid(), now(), now(),
               'LEGACY-PAY-' || replace(p.id::text, '-', ''),
               'BOOKING_PAYMENT', 'POSTED', b.customer_id, p.booking_id, p.amount,
               p.currency, p.payment_method, p.gateway, p.transaction_id, p.notes,
               coalesce(p.paid_at, now()), p.recorded_by_account_id,
               'legacy-booking-payment:' || p.id::text
        FROM booking_payments p
        JOIN bookings b ON b.id = p.booking_id
        WHERE p.status = 'SUCCESS'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id, source.id, t.amount, 0, NULL
        FROM financial_transactions t
        JOIN financial_accounts source ON source.account_code =
            CASE t.payment_method::text
                WHEN 'RAZORPAY' THEN '1020'
                WHEN 'BANK_TRANSFER' THEN '1010'
                ELSE '1000'
            END
        WHERE t.external_reference LIKE 'legacy-booking-payment:%'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id, receivable.id, 0, t.amount, NULL
        FROM financial_transactions t
        JOIN financial_accounts receivable ON receivable.account_code = '1100'
        WHERE t.external_reference LIKE 'legacy-booking-payment:%'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transactions
            (id, created_at, updated_at, transaction_code, transaction_type, status,
             vendor_id, amount, currency, category, reference, description,
             transaction_date, created_by_account_id, external_reference)
        SELECT gen_random_uuid(), e.created_at, e.updated_at,
               'LEGACY-EXP-' || replace(e.id::text, '-', ''),
               'EXPENSE', 'POSTED', e.vendor_id, e.amount, 'INR', e.expense_category,
               e.reference, e.description, e.date, e.created_by_account_id,
               'legacy-expense:' || e.id::text
        FROM expenses e
        WHERE e.is_active = true
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id,
               CASE lower(t.category)
                   WHEN 'hotel' THEN hotel.id
                   WHEN 'transport' THEN transport.id
                   WHEN 'flight' THEN flight.id
                   WHEN 'meal' THEN meal.id
                   WHEN 'activity' THEN activity.id
                   WHEN 'marketing' THEN marketing.id
                   ELSE other_expense.id
               END,
               t.amount, 0, t.description
        FROM financial_transactions t
        CROSS JOIN financial_accounts hotel
        CROSS JOIN financial_accounts transport
        CROSS JOIN financial_accounts flight
        CROSS JOIN financial_accounts meal
        CROSS JOIN financial_accounts activity
        CROSS JOIN financial_accounts marketing
        CROSS JOIN financial_accounts other_expense
        WHERE t.external_reference LIKE 'legacy-expense:%'
          AND hotel.account_code = '5000'
          AND transport.account_code = '5010'
          AND flight.account_code = '5020'
          AND meal.account_code = '5030'
          AND activity.account_code = '5040'
          AND marketing.account_code = '5050'
          AND other_expense.account_code = '5060'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id, source.id, 0, t.amount, t.description
        FROM financial_transactions t
        JOIN financial_accounts source ON source.account_code = '1000'
        WHERE t.external_reference LIKE 'legacy-expense:%'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transactions
            (id, created_at, updated_at, transaction_code, transaction_type, status,
             vendor_id, booking_id, amount, currency, description, transaction_date,
             external_reference)
        SELECT gen_random_uuid(), now(), now(),
               'LEGACY-VPAY-' || replace(vp.id::text, '-', ''),
               'VENDOR_PAYMENT', 'POSTED', bc.vendor_id, bc.booking_id, vp.amount,
               'INR', 'Migrated vendor payment', now(),
               'legacy-vendor-payment:' || vp.id::text
        FROM vendor_payments vp
        JOIN booking_costs bc ON bc.id = vp.booking_cost_id
        WHERE vp.amount > 0
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id, payable.id, t.amount, 0, t.description
        FROM financial_transactions t
        JOIN financial_accounts payable ON payable.account_code = '2000'
        WHERE t.external_reference LIKE 'legacy-vendor-payment:%'
        """
    )
    op.execute(
        """
        INSERT INTO financial_transaction_entries
            (id, created_at, updated_at, transaction_id, account_id, debit, credit, description)
        SELECT gen_random_uuid(), now(), now(), t.id, bank.id, 0, t.amount, t.description
        FROM financial_transactions t
        JOIN financial_accounts bank ON bank.account_code = '1010'
        WHERE t.external_reference LIKE 'legacy-vendor-payment:%'
        """
    )
    op.execute("DROP TABLE booking_payments")
    op.execute("DROP TABLE expenses")
    op.execute("DROP TABLE vendor_payments")
    op.execute("DROP TABLE vendor_expenses")


def downgrade() -> None:
    raise NotImplementedError("Legacy finance tables were intentionally removed after ledger migration.")
