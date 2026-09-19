"""seed wallet adjustment account

Revision ID: 7c8d9e0f1a2b
Revises: 6b7c8d9e0f1a
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7c8d9e0f1a2b"
down_revision: Union[str, Sequence[str], None] = "6b7c8d9e0f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO financial_accounts
            (id, account_code, name, account_type, owner_type, currency, is_active)
        VALUES
            (gen_random_uuid(), '6100', 'Wallet Adjustments', 'EXPENSE', 'SYSTEM', 'INR', true)
        ON CONFLICT (account_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM financial_accounts WHERE account_code = '6100'")
