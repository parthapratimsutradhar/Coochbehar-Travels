"""store enquiry lodging and vehicle preferences as enums

Revision ID: 2ab6d1e8c4f0
Revises: c6b27f4a19d3
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2ab6d1e8c4f0"
down_revision: Union[str, Sequence[str], None] = "c6b27f4a19d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.add_column(
        "enquiries",
        sa.Column(
            "hotel_category",
            postgresql.ENUM(
                "BUDGET",
                "STANDARD",
                "DELUXE",
                "LUXURY",
                name="hotel_category",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "enquiries",
        sa.Column(
            "room_type",
            postgresql.ENUM(
                "SINGLE",
                "DOUBLE",
                "TWIN",
                "TRIPLE",
                "FAMILY",
                "SUITE",
                "DELUXE",
                "EXECUTIVE",
                "PRESIDENTIAL",
                name="room_type",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "enquiries",
        sa.Column(
            "vehicle_type",
            postgresql.ENUM(
                "ANY",
                "NONE",
                "FOUR_SEATER",
                "SIX_SEATER",
                "TEMPO",
                name="vehicle_type",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE enquiries AS e
        SET hotel_category = h.category
        FROM hotels AS h
        WHERE e.hotel_id = h.id
        """
    )
    op.execute(
        """
        UPDATE enquiries AS e
        SET vehicle_type = v.vehicle_type::text::vehicle_type
        FROM vehicles AS v
        WHERE e.vehicle_id = v.id
        """
    )

    op.drop_constraint("enquiries_hotel_id_fkey", "enquiries", type_="foreignkey")
    op.drop_constraint("enquiries_vehicle_id_fkey", "enquiries", type_="foreignkey")
    op.drop_index("ix_enquiries_hotel_id", table_name="enquiries")
    op.drop_index("ix_enquiries_vehicle_id", table_name="enquiries")
    op.drop_column("enquiries", "hotel_id")
    op.drop_column("enquiries", "vehicle_id")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.add_column("enquiries", sa.Column("hotel_id", sa.Uuid(), nullable=True))
    op.add_column("enquiries", sa.Column("vehicle_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "enquiries_hotel_id_fkey",
        "enquiries",
        "hotels",
        ["hotel_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "enquiries_vehicle_id_fkey",
        "enquiries",
        "vehicles",
        ["vehicle_id"],
        ["id"],
    )
    op.create_index("ix_enquiries_hotel_id", "enquiries", ["hotel_id"])
    op.create_index("ix_enquiries_vehicle_id", "enquiries", ["vehicle_id"])
    op.drop_column("enquiries", "hotel_category")
    op.drop_column("enquiries", "room_type")
    op.drop_column("enquiries", "vehicle_type")
