"""widen tour variant slug

Revision ID: b7d3e6a91c42
Revises: a4f2c19b7d31
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d3e6a91c42"
down_revision: Union[str, Sequence[str], None] = "a4f2c19b7d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tour_variants") as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=30),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("tour_variants") as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=255),
            type_=sa.String(length=30),
            existing_nullable=False,
        )