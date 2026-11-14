"""add booking voucher details

Revision ID: c6b27f4a19d3
Revises: 7a4c91d2e630
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6b27f4a19d3"
down_revision: Union[str, Sequence[str], None] = "7a4c91d2e630"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE cost_item_type ADD VALUE IF NOT EXISTS 'HOTEL'")

    op.add_column("trip_hotels", sa.Column("place", sa.String(length=255), nullable=True))
    op.add_column("trip_hotels", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("trip_hotels", sa.Column("contact_person", sa.String(length=100), nullable=True))
    op.add_column("trip_hotels", sa.Column("contact_number", sa.String(length=100), nullable=True))
    op.add_column(
        "trip_hotels",
        sa.Column("paid_by_traveller", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    op.add_column("trip_vehicles", sa.Column("pickup_location", sa.String(length=255), nullable=True))
    op.add_column("trip_vehicles", sa.Column("drop_location", sa.String(length=255), nullable=True))
    op.add_column("trip_vehicles", sa.Column("owner_name", sa.String(length=100), nullable=True))
    op.add_column("trip_vehicles", sa.Column("owner_contact", sa.String(length=100), nullable=True))
    op.add_column("trip_vehicles", sa.Column("driver_name", sa.String(length=100), nullable=True))
    op.add_column("trip_vehicles", sa.Column("driver_contact", sa.String(length=100), nullable=True))
    op.add_column("trip_vehicles", sa.Column("registration_number", sa.String(length=50), nullable=True))
    op.add_column(
        "trip_vehicles",
        sa.Column("paid_by_traveller", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.drop_column("hotels", "contact")
    op.drop_column("vehicles", "price_per_day")


def downgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column("price_per_day", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.alter_column("vehicles", "price_per_day", server_default=None)
    op.add_column("hotels", sa.Column("contact", sa.String(length=100), nullable=True))
    op.drop_column("trip_vehicles", "paid_by_traveller")
    op.drop_column("trip_vehicles", "registration_number")
    op.drop_column("trip_vehicles", "driver_contact")
    op.drop_column("trip_vehicles", "driver_name")
    op.drop_column("trip_vehicles", "owner_contact")
    op.drop_column("trip_vehicles", "owner_name")
    op.drop_column("trip_vehicles", "drop_location")
    op.drop_column("trip_vehicles", "pickup_location")

    op.drop_column("trip_hotels", "paid_by_traveller")
    op.drop_column("trip_hotels", "contact_number")
    op.drop_column("trip_hotels", "contact_person")
    op.drop_column("trip_hotels", "address")
    op.drop_column("trip_hotels", "place")
