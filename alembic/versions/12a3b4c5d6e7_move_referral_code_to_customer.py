"""move referral code to customer

Revision ID: 12a3b4c5d6e7
Revises: 11a17ae79ed1
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "12a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "11a17ae79ed1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("referral_code", sa.String(length=30), nullable=True),
    )
    op.execute(
        "UPDATE customers SET referral_code = 'REF-' || customer_code"
    )
    op.alter_column("customers", "referral_code", nullable=False)
    op.create_index(
        "ix_customers_referral_code",
        "customers",
        ["referral_code"],
        unique=True,
    )

    op.drop_index("ix_referrals_referral_code", table_name="referrals")
    op.drop_column("referrals", "referral_code")


def downgrade() -> None:
    op.add_column(
        "referrals",
        sa.Column("referral_code", sa.String(length=30), nullable=True),
    )
    op.execute(
        "UPDATE referrals SET referral_code = 'REF-' || substr(id::text, 1, 24)"
    )
    op.alter_column("referrals", "referral_code", nullable=False)
    op.create_index(
        "ix_referrals_referral_code",
        "referrals",
        ["referral_code"],
        unique=True,
    )

    op.drop_index("ix_customers_referral_code", table_name="customers")
    op.drop_column("customers", "referral_code")
