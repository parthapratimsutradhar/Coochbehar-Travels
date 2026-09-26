"""fix finance models

Revision ID: 01a6e5b41eaa
Revises: c4d5e6f7a8b9
Create Date: 2026-09-26 14:28:37.805546
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "01a6e5b41eaa"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # PostgreSQL blocks dropping parent tables when child tables still depend on them.
    # Use CASCADE for this migration so the dependent FK objects are removed together.
    op.execute("DROP TABLE IF EXISTS quotation_vehicles CASCADE")
    op.execute("DROP TABLE IF EXISTS quotation_hotels CASCADE")
    op.execute("DROP TABLE IF EXISTS quotation_items CASCADE")
    op.execute("DROP TABLE IF EXISTS vendor_bookings CASCADE")
    op.execute("DROP TABLE IF EXISTS booking_costs CASCADE")

    # Ensure enum types exist before altering dependent columns.
    booking_status_enum = sa.Enum(
        "TENTATIVE",
        "CONFIRMED",
        "PARTIALLY_PAID",
        "FULLY_PAID",
        "TRAVELLED",
        "COMPLETED",
        "ON_HOLD",
        "CANCELLED",
        "REFUNDED",
        name="booking_status",
    )
    booking_status_enum.create(op.get_bind(), checkfirst=True)

    gender_enum = sa.Enum("MALE", "FEMALE", "OTHER", name="gender")
    gender_enum.create(op.get_bind(), checkfirst=True)

    tour_type_enum = sa.Enum("DOMESTIC", "INTERNATIONAL", name="tour_type")
    tour_type_enum.create(op.get_bind(), checkfirst=True)

    financial_transaction_category_enum = sa.Enum(
        "REFERRAL_INCOME",
        "BOOKING_PAYMENT",
        "BOOKING_REFUND",
        "WALLET_CREDIT",
        "WALLET_DEBIT",
        "VENDOR_PAYMENT",
        "TRANSFER",
        "ADJUSTMENT",
        "REFERRAL_REWARD",
        name="financial_transaction_category",
    )
    financial_transaction_category_enum.create(op.get_bind(), checkfirst=True)

    # Booking status history.
    op.add_column(
        "booking_status_history",
        sa.Column(
            "new_status",
            booking_status_enum,
            nullable=False,
        ),
    )
    op.drop_column("booking_status_history", "status")

    # Booking travelers.
    op.execute(
        "ALTER TABLE booking_travelers ALTER COLUMN gender TYPE gender USING gender::gender"
    )
    op.drop_column("booking_travelers", "traveler_type")

    # Booking type.
    op.execute(
        "ALTER TABLE bookings ALTER COLUMN booking_type TYPE tour_type USING booking_type::tour_type"
    )

    # Financial transaction category.
    op.execute(
        "ALTER TABLE financial_transactions ALTER COLUMN category TYPE financial_transaction_category USING category::financial_transaction_category"
    )

    # Quotation indexes.
    op.drop_index(
        op.f("ix_quotations_created_by_account_id"),
        table_name="quotations",
    )
    op.drop_index(
        op.f("ix_quotations_status"),
        table_name="quotations",
    )

    # Trip hotel uniqueness.
    op.drop_constraint(
        op.f("trip_hotels_trip_item_id_key"),
        "trip_hotels",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_trip_hotels_trip_item_id"),
        table_name="trip_hotels",
    )
    op.create_index(
        op.f("ix_trip_hotels_trip_item_id"),
        "trip_hotels",
        ["trip_item_id"],
        unique=True,
    )

    # Trip vehicle uniqueness.
    op.drop_constraint(
        op.f("trip_vehicles_trip_item_id_key"),
        "trip_vehicles",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_trip_vehicles_trip_item_id"),
        table_name="trip_vehicles",
    )
    op.create_index(
        op.f("ix_trip_vehicles_trip_item_id"),
        "trip_vehicles",
        ["trip_item_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Trip vehicle uniqueness.
    op.drop_index(
        op.f("ix_trip_vehicles_trip_item_id"),
        table_name="trip_vehicles",
    )
    op.create_index(
        op.f("ix_trip_vehicles_trip_item_id"),
        "trip_vehicles",
        ["trip_item_id"],
        unique=False,
    )
    op.create_unique_constraint(
        op.f("trip_vehicles_trip_item_id_key"),
        "trip_vehicles",
        ["trip_item_id"],
        postgresql_nulls_not_distinct=False,
    )

    # Trip hotel uniqueness.
    op.drop_index(
        op.f("ix_trip_hotels_trip_item_id"),
        table_name="trip_hotels",
    )
    op.create_index(
        op.f("ix_trip_hotels_trip_item_id"),
        "trip_hotels",
        ["trip_item_id"],
        unique=False,
    )
    op.create_unique_constraint(
        op.f("trip_hotels_trip_item_id_key"),
        "trip_hotels",
        ["trip_item_id"],
        postgresql_nulls_not_distinct=False,
    )

    # Quotation indexes.
    op.create_index(
        op.f("ix_quotations_status"),
        "quotations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quotations_created_by_account_id"),
        "quotations",
        ["created_by_account_id"],
        unique=False,
    )

    # Financial transaction category.
    op.alter_column(
        "financial_transactions",
        "category",
        existing_type=sa.Enum(
            "REFERRAL_INCOME",
            "BOOKING_PAYMENT",
            "BOOKING_REFUND",
            "WALLET_CREDIT",
            "WALLET_DEBIT",
            "VENDOR_PAYMENT",
            "TRANSFER",
            "ADJUSTMENT",
            "REFERRAL_REWARD",
            name="financial_transaction_category",
        ),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )

    # Booking type.
    op.alter_column(
        "bookings",
        "booking_type",
        existing_type=sa.Enum(
            "DOMESTIC",
            "INTERNATIONAL",
            name="tour_type",
        ),
        type_=sa.VARCHAR(length=30),
        existing_nullable=False,
    )

    # Booking travelers.
    op.add_column(
        "booking_travelers",
        sa.Column(
            "traveler_type",
            sa.VARCHAR(length=20),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.alter_column(
        "booking_travelers",
        "gender",
        existing_type=sa.Enum(
            "MALE",
            "FEMALE",
            "OTHER",
            name="gender",
        ),
        type_=sa.VARCHAR(length=20),
        existing_nullable=True,
    )

    # Booking status history.
    op.add_column(
        "booking_status_history",
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "CONFIRMED",
                "CANCELLED",
                "COMPLETED",
                "TENTATIVE",
                "PARTIALLY_PAID",
                "FULLY_PAID",
                "TRAVELLED",
                "ON_HOLD",
                "REFUNDED",
                name="booking_status",
            ),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_column("booking_status_history", "new_status")

    # quotation_hotels.
    op.create_table(
        "quotation_hotels",
        sa.Column(
            "quotation_item_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "hotel_id",
            sa.UUID(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "hotel_name",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "check_in",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "check_out",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["hotel_id"],
            ["hotels.id"],
            name=op.f("quotation_hotels_hotel_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["quotation_item_id"],
            ["quotation_items.id"],
            name=op.f("quotation_hotels_quotation_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("quotation_hotels_pkey"),
        ),
    )
    op.create_index(
        op.f("ix_quotation_hotels_quotation_item_id"),
        "quotation_hotels",
        ["quotation_item_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_quotation_hotels_hotel_id"),
        "quotation_hotels",
        ["hotel_id"],
        unique=False,
    )

    # vendor_bookings.
    op.create_table(
        "vendor_bookings",
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "vendor_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "cost_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("vendor_bookings_booking_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["cost_id"],
            ["booking_costs.id"],
            name=op.f("vendor_bookings_cost_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            name=op.f("vendor_bookings_vendor_id_fkey"),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("vendor_bookings_pkey"),
        ),
    )

    # booking_costs.
    op.create_table(
        "booking_costs",
        sa.Column(
            "booking_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "cost_type",
            sa.VARCHAR(length=50),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.VARCHAR(length=200),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "vendor_id",
            sa.UUID(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "estimated_amount",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "actual_amount",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "paid_amount",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "due_amount",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.VARCHAR(length=30),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "actual_amount >= 0::numeric",
            name=op.f("ck_booking_cost_actual_nonnegative"),
        ),
        sa.CheckConstraint(
            "due_amount >= 0::numeric",
            name=op.f("ck_booking_cost_due_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_amount >= 0::numeric",
            name=op.f("ck_booking_cost_estimated_nonnegative"),
        ),
        sa.CheckConstraint(
            "paid_amount <= actual_amount",
            name=op.f("ck_booking_cost_paid_not_over_actual"),
        ),
        sa.CheckConstraint(
            "paid_amount >= 0::numeric",
            name=op.f("ck_booking_cost_paid_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("booking_costs_booking_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendors.id"],
            name=op.f("booking_costs_vendor_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("booking_costs_pkey"),
        ),
    )
    op.create_index(
        op.f("ix_booking_costs_vendor_id"),
        "booking_costs",
        ["vendor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_booking_costs_booking_id"),
        "booking_costs",
        ["booking_id"],
        unique=False,
    )

    # quotation_items.
    op.create_table(
        "quotation_items",
        sa.Column(
            "quotation_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "item_type",
            postgresql.ENUM(
                "HOTEL",
                "TRANSPORT",
                "FLIGHT",
                "TRAIN",
                "MEAL",
                "ACTIVITY",
                "GUIDE",
                "PERMIT",
                "TRANSFER",
                "OTHER",
                name="quotation_item_type",
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "quantity",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "total_price",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_quotation_item_quantity_positive"),
        ),
        sa.CheckConstraint(
            "total_price >= 0::numeric",
            name=op.f("ck_quotation_item_total_price_non_negative"),
        ),
        sa.CheckConstraint(
            "unit_price >= 0::numeric",
            name=op.f("ck_quotation_item_unit_price_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["quotation_id"],
            ["quotations.id"],
            name=op.f("quotation_items_quotation_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("quotation_items_pkey"),
        ),
    )
    op.create_index(
        op.f("ix_quotation_items_quotation_id"),
        "quotation_items",
        ["quotation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quotation_items_item_type"),
        "quotation_items",
        ["item_type"],
        unique=False,
    )

    # quotation_vehicles.
    op.create_table(
        "quotation_vehicles",
        sa.Column(
            "quotation_item_id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.UUID(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "vehicle_name",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "vehicle_type",
            sa.VARCHAR(length=100),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "quantity",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "start_date",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "end_date",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "days",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "unit_price",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "total_price",
            sa.NUMERIC(precision=12, scale=2),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["quotation_item_id"],
            ["quotation_items.id"],
            name=op.f("quotation_vehicles_quotation_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name=op.f("quotation_vehicles_vehicle_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("quotation_vehicles_pkey"),
        ),
    )
    op.create_index(
        op.f("ix_quotation_vehicles_vehicle_id"),
        "quotation_vehicles",
        ["vehicle_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quotation_vehicles_quotation_item_id"),
        "quotation_vehicles",
        ["quotation_item_id"],
        unique=True,
    )