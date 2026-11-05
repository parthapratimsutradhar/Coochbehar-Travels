"""add promotional contacts

Revision ID: 71a2c9e4d6f0
Revises: f5c73d0a91be
Create Date: 2026-11-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "71a2c9e4d6f0"
down_revision: Union[str, Sequence[str], None] = "f5c73d0a91be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promonal_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promonal_contacts_mobile", "promonal_contacts", ["mobile"])
    op.create_index("ix_promonal_contacts_email", "promonal_contacts", ["email"])


def downgrade() -> None:
    op.drop_index("ix_promonal_contacts_email", table_name="promonal_contacts")
    op.drop_index("ix_promonal_contacts_mobile", table_name="promonal_contacts")
    op.drop_table("promonal_contacts")
