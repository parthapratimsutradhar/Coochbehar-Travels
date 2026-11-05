"""remove hotel and vehicle image fields

Revision ID: 7a4c91d2e630
Revises: f5c73d0a91be
Create Date: 2026-11-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "7a4c91d2e630"
down_revision: Union[str, Sequence[str], None] = "71a2c9e4d6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("hotels", "image")
    op.drop_column("vehicles", "vehicle_image")


def downgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column(
            "vehicle_image",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("vehicles", "vehicle_image", server_default=None)
    op.add_column(
        "hotels",
        sa.Column(
            "image",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("hotels", "image", server_default=None)
