"""add booking document types to PostgreSQL enum

Revision ID: f5c73d0a91be
Revises: e42f8d91c6ab
Create Date: 2026-10-09

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f5c73d0a91be"
down_revision: Union[str, Sequence[str], None] = "e42f8d91c6ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'FLIGHT_TICKET'")
    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'TRAIN_TICKET'")
    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'HOTEL_VOUCHER'")


def downgrade() -> None:
    pass
