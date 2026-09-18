"""update quotation travel fields

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5c7
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("quotations", "destination")
    op.drop_column("quotations", "vehicle")
    op.drop_column("quotations", "notes")

    op.add_column("quotations", sa.Column("hotel_id", sa.UUID(), nullable=True))
    op.add_column("quotations", sa.Column("room_id", sa.UUID(), nullable=True))
    op.add_column("quotations", sa.Column("vehicle_id", sa.UUID(), nullable=True))
    op.add_column("quotations", sa.Column("vehicle_count", sa.Integer(), nullable=True))
    op.add_column("quotations", sa.Column("rejected_reason", sa.Text(), nullable=True))

    op.create_index(op.f("ix_quotations_hotel_id"), "quotations", ["hotel_id"], unique=False)
    op.create_index(op.f("ix_quotations_room_id"), "quotations", ["room_id"], unique=False)
    op.create_index(op.f("ix_quotations_vehicle_id"), "quotations", ["vehicle_id"], unique=False)
    op.create_foreign_key(
        "fk_quotations_hotel_id_hotels",
        "quotations",
        "hotels",
        ["hotel_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_quotations_room_id_rooms",
        "quotations",
        "rooms",
        ["room_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_quotations_vehicle_id_vehicles",
        "quotations",
        "vehicles",
        ["vehicle_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotations_vehicle_id_vehicles", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_room_id_rooms", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_hotel_id_hotels", "quotations", type_="foreignkey")
    op.drop_index(op.f("ix_quotations_vehicle_id"), table_name="quotations")
    op.drop_index(op.f("ix_quotations_room_id"), table_name="quotations")
    op.drop_index(op.f("ix_quotations_hotel_id"), table_name="quotations")
    op.drop_column("quotations", "rejected_reason")
    op.drop_column("quotations", "vehicle_count")
    op.drop_column("quotations", "vehicle_id")
    op.drop_column("quotations", "room_id")
    op.drop_column("quotations", "hotel_id")
    op.add_column("quotations", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("quotations", sa.Column("vehicle", sa.String(length=100), nullable=True))
    op.add_column("quotations", sa.Column("destination", sa.String(length=255), nullable=True))
