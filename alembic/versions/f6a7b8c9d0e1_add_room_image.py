"""add images to rooms

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    room_columns = {column["name"] for column in inspector.get_columns("rooms")}

    if "room_image" not in room_columns:
        op.add_column(
            "rooms",
            sa.Column("room_image", postgresql.JSONB(), nullable=True),
        )
        op.execute("UPDATE rooms SET room_image = '[]'::jsonb WHERE room_image IS NULL")
        op.alter_column(
            "rooms",
            "room_image",
            existing_type=postgresql.JSONB(),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    room_columns = {column["name"] for column in inspector.get_columns("rooms")}
    if "room_image" in room_columns:
        op.drop_column("rooms", "room_image")