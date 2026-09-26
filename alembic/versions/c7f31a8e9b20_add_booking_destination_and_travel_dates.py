"""persist booking destination and travel dates

Revision ID: c7f31a8e9b20
Revises: 01a6e5b41eaa
Create Date: 2026-09-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7f31a8e9b20"
down_revision: Union[str, Sequence[str], None] = "01a6e5b41eaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("bookings", sa.Column("departure_date", sa.Date(), nullable=True))
    op.add_column("bookings", sa.Column("return_date", sa.Date(), nullable=True))
    op.create_index("ix_bookings_destination_id", "bookings", ["destination_id"])
    op.create_foreign_key(
        "fk_bookings_destination_id_destinations",
        "bookings",
        "destinations",
        ["destination_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_bookings_destination_id_destinations",
        "bookings",
        type_="foreignkey",
    )
    op.drop_index("ix_bookings_destination_id", table_name="bookings")
    op.drop_column("bookings", "return_date")
    op.drop_column("bookings", "departure_date")
    op.drop_column("bookings", "destination_id")