"""add INCOME to financial transaction type

Revision ID: d2e3f4a5b6c7
Revises: c7f31a8e9b20
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c7f31a8e9b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE financial_transaction_type ADD VALUE IF NOT EXISTS 'INCOME'")


def downgrade() -> None:
    pass