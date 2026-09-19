"""fix enquiry hotel foreign key

Revision ID: 9a0b1c2d3e4f
Revises: 8d9e0f1a2b3c
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a0b1c2d3e4f"
down_revision: Union[str, Sequence[str], None] = "8d9e0f1a2b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for foreign_key in inspector.get_foreign_keys("enquiries"):
        if (
            foreign_key.get("constrained_columns") == ["hotel_id"]
            and foreign_key.get("referred_table") == "rooms"
        ):
            op.drop_constraint(
                foreign_key["name"],
                "enquiries",
                type_="foreignkey",
            )

    op.execute(
        sa.text(
            """
            UPDATE enquiries AS enquiries
            SET hotel_id = rooms.hotel_id
            FROM rooms
            WHERE enquiries.hotel_id = rooms.id
            """
        )
    )

    op.create_foreign_key(
        "fk_enquiries_hotel_id_hotels",
        "enquiries",
        "hotels",
        ["hotel_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_enquiries_hotel_id_hotels",
        "enquiries",
        type_="foreignkey",
    )
    op.execute(sa.text("UPDATE enquiries SET hotel_id = NULL"))
    op.create_foreign_key(
        "fk_enquiries_hotel_id_rooms",
        "enquiries",
        "rooms",
        ["hotel_id"],
        ["id"],
    )
