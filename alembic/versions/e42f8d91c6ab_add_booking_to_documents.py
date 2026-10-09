"""add booking association to documents

Revision ID: e42f8d91c6ab
Revises: d18c4a7e92bf
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e42f8d91c6ab"
down_revision: Union[str, Sequence[str], None] = "d18c4a7e92bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("booking_id", sa.Uuid(), nullable=True))
    op.create_index("ix_documents_booking_id", "documents", ["booking_id"])
    op.create_foreign_key(
        "documents_booking_id_fkey",
        "documents",
        "bookings",
        ["booking_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("documents_booking_id_fkey", "documents", type_="foreignkey")
    op.drop_index("ix_documents_booking_id", table_name="documents")
    op.drop_column("documents", "booking_id")