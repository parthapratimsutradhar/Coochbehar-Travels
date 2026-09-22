"""align vendors table with the current vendor model

Revision ID: b1c2d3e4f5a6
Revises: 9e0f1a2b3c4d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "9e0f1a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_vendors_vendor_code", table_name="vendors")
    op.drop_column("vendors", "vendor_code")
    op.drop_column("vendors", "payment_terms")
    op.drop_column("vendors", "status")


def downgrade() -> None:
    op.add_column("vendors", sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"))
    op.add_column("vendors", sa.Column("payment_terms", sa.String(length=100), nullable=True))
    op.add_column("vendors", sa.Column("vendor_code", sa.String(length=20), nullable=True))
    op.create_index("ix_vendors_vendor_code", "vendors", ["vendor_code"], unique=True)
    op.alter_column("vendors", "status", server_default=None)