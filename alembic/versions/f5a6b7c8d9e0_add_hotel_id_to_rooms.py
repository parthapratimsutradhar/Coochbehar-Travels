"""add hotel ownership to rooms

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    room_columns = {column["name"] for column in inspector.get_columns("rooms")}

    room_type = postgresql.ENUM(
        "SINGLE", "DOUBLE", "TWIN", "TRIPLE", "FAMILY", "SUITE",
        "DELUXE", "EXECUTIVE", "PRESIDENTIAL", name="room_type",
    )
    room_type.create(bind, checkfirst=True)

    if "hotel_id" not in room_columns:
        op.add_column("rooms", sa.Column("hotel_id", sa.UUID(), nullable=True))

    foreign_keys = inspector.get_foreign_keys("rooms")
    has_hotel_foreign_key = any(
        foreign_key.get("constrained_columns") == ["hotel_id"]
        and foreign_key.get("referred_table") == "hotels"
        for foreign_key in foreign_keys
    )
    if not has_hotel_foreign_key:
        op.create_foreign_key(
            "fk_rooms_hotel_id_hotels",
            "rooms",
            "hotels",
            ["hotel_id"],
            ["id"],
            ondelete="CASCADE",
        )

    indexes = inspector.get_indexes("rooms")
    has_hotel_index = any(index.get("column_names") == ["hotel_id"] for index in indexes)
    if not has_hotel_index:
        op.create_index("ix_rooms_hotel_id", "rooms", ["hotel_id"], unique=False)

    room_column = next(column for column in inspector.get_columns("rooms") if column["name"] == "room_type")
    if not isinstance(room_column["type"], postgresql.ENUM):
        op.alter_column(
            "rooms",
            "room_type",
            existing_type=sa.String(length=50),
            type_=room_type,
            existing_nullable=True,
            postgresql_using="CASE UPPER(room_type) WHEN 'SINGLE' THEN 'SINGLE'::room_type WHEN 'DOUBLE' THEN 'DOUBLE'::room_type WHEN 'TWIN' THEN 'TWIN'::room_type WHEN 'TRIPLE' THEN 'TRIPLE'::room_type WHEN 'FAMILY' THEN 'FAMILY'::room_type WHEN 'SUITE' THEN 'SUITE'::room_type WHEN 'DELUXE' THEN 'DELUXE'::room_type WHEN 'EXECUTIVE' THEN 'EXECUTIVE'::room_type WHEN 'PRESIDENTIAL' THEN 'PRESIDENTIAL'::room_type ELSE NULL END",
        )


def downgrade() -> None:
    op.alter_column(
        "rooms",
        "room_type",
        existing_type=postgresql.ENUM(
            "SINGLE", "DOUBLE", "TWIN", "TRIPLE", "FAMILY", "SUITE",
            "DELUXE", "EXECUTIVE", "PRESIDENTIAL", name="room_type",
        ),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using="room_type::text",
    )
    op.drop_index("ix_rooms_hotel_id", table_name="rooms")
    op.drop_constraint("fk_rooms_hotel_id_hotels", "rooms", type_="foreignkey")
    op.drop_column("rooms", "hotel_id")
    postgresql.ENUM(name="room_type").drop(op.get_bind(), checkfirst=True)