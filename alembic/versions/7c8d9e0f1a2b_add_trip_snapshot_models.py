"""add trip snapshot models

Revision ID: 9e0f1a2b3c4d
Revises: 4e7e84dbc552
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9e0f1a2b3c4d"
down_revision: Union[str, Sequence[str], None] = "4e7e84dbc552"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "HOTEL", "TRANSPORT", "FLIGHT", "TRAIN", "MEAL",
        "ACTIVITY", "GUIDE", "PERMIT", "TRANSFER", "OTHER",
        name="cost_item_type",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "ANY", "NONE", "FOUR_SEATER", "SIX_SEATER", "TEMPO",
        name="vehicle_type",
    ).create(bind, checkfirst=True)

    op.create_table(
        "trip_items",
        sa.Column("quotation_id", sa.UUID(), nullable=True),
        sa.Column("booking_id", sa.UUID(), nullable=True),
        sa.Column(
            "item_type",
            postgresql.ENUM(
                "HOTEL", "TRANSPORT", "FLIGHT", "TRAIN", "MEAL",
                "ACTIVITY", "GUIDE", "PERMIT", "TRANSFER", "OTHER",
                name="cost_item_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_trip_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_trip_item_unit_price_non_negative"),
        sa.CheckConstraint("total_price >= 0", name="ck_trip_item_total_price_non_negative"),
        sa.CheckConstraint(
            "(quotation_id IS NOT NULL) <> (booking_id IS NOT NULL)",
            name="ck_trip_item_single_owner",
        ),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_items_quotation_id", "trip_items", ["quotation_id"])
    op.create_index("ix_trip_items_booking_id", "trip_items", ["booking_id"])
    op.create_index("ix_trip_items_item_type", "trip_items", ["item_type"])

    op.create_table(
        "trip_itinerary",
        sa.Column("quotation_id", sa.UUID(), nullable=True),
        sa.Column("booking_id", sa.UUID(), nullable=True),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("overnight_location", sa.String(length=255), nullable=True),
        sa.Column(
            "meal_plan",
            postgresql.ENUM(
                "ANY", "NONE", "CP", "MAP", "AP",
                name="meal_plan",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("day_number > 0", name="ck_trip_itinerary_day_positive"),
        sa.CheckConstraint(
            "(quotation_id IS NOT NULL) <> (booking_id IS NOT NULL)",
            name="ck_trip_itinerary_single_owner",
        ),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_id", "day_number", name="uq_quotation_itinerary_day"),
        sa.UniqueConstraint("booking_id", "day_number", name="uq_booking_itinerary_day"),
    )
    op.create_index("ix_trip_itinerary_quotation_id", "trip_itinerary", ["quotation_id"])
    op.create_index("ix_trip_itinerary_booking_id", "trip_itinerary", ["booking_id"])

    op.create_table(
        "trip_hotels",
        sa.Column("trip_item_id", sa.UUID(), nullable=False),
        sa.Column("hotel_id", sa.UUID(), nullable=True),
        sa.Column("hotel_name", sa.String(length=255), nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nights", sa.Integer(), nullable=False),
        sa.Column("room_count", sa.Integer(), nullable=False),
        sa.Column(
            "room_type",
            postgresql.ENUM(
                "SINGLE", "DOUBLE", "TWIN", "TRIPLE", "FAMILY", "SUITE",
                "DELUXE", "EXECUTIVE", "PRESIDENTIAL",
                name="room_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("check_out > check_in", name="ck_trip_hotel_checkout_after_checkin"),
        sa.CheckConstraint("nights > 0", name="ck_trip_hotel_nights_positive"),
        sa.CheckConstraint("room_count > 0", name="ck_trip_hotel_room_count_positive"),
        sa.ForeignKeyConstraint(["trip_item_id"], ["trip_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_item_id"),
    )
    op.create_index("ix_trip_hotels_trip_item_id", "trip_hotels", ["trip_item_id"])
    op.create_index("ix_trip_hotels_hotel_id", "trip_hotels", ["hotel_id"])

    op.create_table(
        "trip_vehicles",
        sa.Column("trip_item_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_id", sa.UUID(), nullable=True),
        sa.Column("vehicle_name", sa.String(length=255), nullable=False),
        sa.Column(
            "vehicle_type",
            postgresql.ENUM(
                "ANY", "NONE", "FOUR_SEATER", "SIX_SEATER", "TEMPO",
                name="vehicle_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rental_minutes", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("end_date > start_date", name="ck_trip_vehicle_end_after_start"),
        sa.CheckConstraint("rental_minutes > 0", name="ck_trip_vehicle_rental_minutes_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_trip_vehicle_quantity_positive"),
        sa.ForeignKeyConstraint(["trip_item_id"], ["trip_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_item_id"),
    )
    op.create_index("ix_trip_vehicles_trip_item_id", "trip_vehicles", ["trip_item_id"])
    op.create_index("ix_trip_vehicles_vehicle_id", "trip_vehicles", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_trip_vehicles_vehicle_id", table_name="trip_vehicles")
    op.drop_index("ix_trip_vehicles_trip_item_id", table_name="trip_vehicles")
    op.drop_table("trip_vehicles")
    op.drop_index("ix_trip_hotels_hotel_id", table_name="trip_hotels")
    op.drop_index("ix_trip_hotels_trip_item_id", table_name="trip_hotels")
    op.drop_table("trip_hotels")
    op.drop_index("ix_trip_itinerary_booking_id", table_name="trip_itinerary")
    op.drop_index("ix_trip_itinerary_quotation_id", table_name="trip_itinerary")
    op.drop_table("trip_itinerary")
    op.drop_index("ix_trip_items_item_type", table_name="trip_items")
    op.drop_index("ix_trip_items_booking_id", table_name="trip_items")
    op.drop_index("ix_trip_items_quotation_id", table_name="trip_items")
    op.drop_table("trip_items")
    op.execute("DROP TYPE IF EXISTS vehicle_type")
    op.execute("DROP TYPE IF EXISTS room_type")
    op.execute("DROP TYPE IF EXISTS meal_plan")
    op.execute("DROP TYPE IF EXISTS cost_item_type")
