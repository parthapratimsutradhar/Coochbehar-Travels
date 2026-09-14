"""add timestamps to tour offers

Revision ID: 6e1f2a3b4c5d
Revises: 5d0e1f2a3b4c
Create Date: 2026-09-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e1f2a3b4c5d"
down_revision: Union[str, Sequence[str], None] = "5d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tour_offers",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "tour_offers",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("tour_offers", "updated_at")
    op.drop_column("tour_offers", "created_at")
