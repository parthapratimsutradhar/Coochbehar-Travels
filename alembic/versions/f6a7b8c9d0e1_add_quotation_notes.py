"""add quotation notes and inclusions

Revision ID: f9a0b1c2d3e4
Revises: e5f6a7b8c9d0
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quotations", sa.Column("important_notes", sa.Text(), nullable=True))
    op.add_column("quotations", sa.Column("inclusion", sa.Text(), nullable=True))
    op.add_column("quotations", sa.Column("exclusion", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("quotations", "exclusion")
    op.drop_column("quotations", "inclusion")
    op.drop_column("quotations", "important_notes")