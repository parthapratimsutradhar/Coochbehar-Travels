"""add images to vehicles

Revision ID: f8a9b0c1d2e3
Revises: f6a7b8c9d0e1
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    if "vehicle_image" not in vehicle_columns:
        op.add_column(
            "vehicles",
            sa.Column("vehicle_image", postgresql.JSONB(), nullable=True),
        )
        op.execute("UPDATE vehicles SET vehicle_image = '[]'::jsonb WHERE vehicle_image IS NULL")
        op.alter_column(
            "vehicles",
            "vehicle_image",
            existing_type=postgresql.JSONB(),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    if "vehicle_image" in vehicle_columns:
        op.drop_column("vehicles", "vehicle_image")