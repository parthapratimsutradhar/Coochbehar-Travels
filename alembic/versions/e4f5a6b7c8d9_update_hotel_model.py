"""align hotels table with hotel model

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    hotel_category = postgresql.ENUM(
        "BUDGET",
        "STANDARD",
        "DELUXE",
        "LUXURY",
        name="hotel_category",
    )
    hotel_category.create(op.get_bind(), checkfirst=True)

    op.add_column("hotels", sa.Column("image", postgresql.JSONB(), nullable=True))
    op.execute("UPDATE hotels SET image = '[]'::jsonb WHERE image IS NULL")
    op.alter_column("hotels", "image", nullable=False)

    op.alter_column(
        "hotels",
        "category",
        existing_type=sa.String(length=50),
        type_=hotel_category,
        existing_nullable=True,
        postgresql_using=(
            "CASE UPPER(category) "
            "WHEN 'BUDGET' THEN 'BUDGET'::hotel_category "
            "WHEN 'STANDARD' THEN 'STANDARD'::hotel_category "
            "WHEN 'DELUXE' THEN 'DELUXE'::hotel_category "
            "WHEN 'LUXURY' THEN 'LUXURY'::hotel_category "
            "ELSE NULL END"
        ),
    )

    op.drop_column("hotels", "destination")


def downgrade() -> None:
    op.add_column(
        "hotels",
        sa.Column("destination", sa.String(length=255), nullable=True),
    )
    op.alter_column(
        "hotels",
        "category",
        existing_type=postgresql.ENUM(
            "BUDGET",
            "STANDARD",
            "DELUXE",
            "LUXURY",
            name="hotel_category",
        ),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using="category::text",
    )
    op.drop_column("hotels", "image")
    postgresql.ENUM(name="hotel_category").drop(op.get_bind(), checkfirst=True)
