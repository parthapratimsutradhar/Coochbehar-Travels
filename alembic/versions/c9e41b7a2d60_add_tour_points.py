"""add tour points, configurations, and transaction history

Revision ID: c9e41b7a2d60
Revises: b7d3e6a91c42
Create Date: 2026-10-04

"""
from datetime import datetime, timezone
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e41b7a2d60"
down_revision: Union[str, Sequence[str], None] = "b7d3e6a91c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.add_column(sa.Column("departure_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_quotations_departure_id", ["departure_id"])
        batch_op.create_foreign_key(
            "fk_quotations_departure_id_tour_departures",
            "tour_departures",
            ["departure_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.add_column(
        "accounts",
        sa.Column("points_balance", sa.Numeric(20, 4), nullable=False, server_default="0"),
    )

    op.create_table(
        "tour_point_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tour_type", sa.String(length=20), nullable=False),
        sa.Column("amount_per_point", sa.Numeric(12, 2), nullable=False),
        sa.Column("updated_by_account_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tour_type", name="uq_tour_point_configuration_type"),
    )
    op.create_table(
        "tour_point_configuration_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("configuration_id", sa.Uuid(), nullable=True),
        sa.Column("tour_type", sa.String(length=20), nullable=False),
        sa.Column("previous_amount_per_point", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount_per_point", sa.Numeric(12, 2), nullable=False),
        sa.Column("changed_by_account_id", sa.Uuid(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["configuration_id"], ["tour_point_configurations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["changed_by_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tour_point_configuration_history_configuration_id",
        "tour_point_configuration_history",
        ["configuration_id"],
    )
    op.create_index(
        "ix_tour_point_configuration_history_tour_type",
        "tour_point_configuration_history",
        ["tour_type"],
    )

    now = datetime.now(timezone.utc)
    configurations = [
        {"id": uuid.uuid4(), "tour_type": tour_type, "amount_per_point": 10000, "created_at": now, "updated_at": now}
        for tour_type in ("DOMESTIC", "INTERNATIONAL")
    ]
    op.bulk_insert(
        sa.table(
            "tour_point_configurations",
            sa.column("id", sa.Uuid()),
            sa.column("tour_type", sa.String(20)),
            sa.column("amount_per_point", sa.Numeric(12, 2)),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        configurations,
    )
    op.bulk_insert(
        sa.table(
            "tour_point_configuration_history",
            sa.column("id", sa.Uuid()),
            sa.column("configuration_id", sa.Uuid()),
            sa.column("tour_type", sa.String(20)),
            sa.column("previous_amount_per_point", sa.Numeric(12, 2)),
            sa.column("amount_per_point", sa.Numeric(12, 2)),
            sa.column("changed_by_account_id", sa.Uuid()),
            sa.column("changed_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": uuid.uuid4(),
                "configuration_id": config["id"],
                "tour_type": config["tour_type"],
                "previous_amount_per_point": None,
                "amount_per_point": config["amount_per_point"],
                "changed_by_account_id": None,
                "changed_at": now,
            }
            for config in configurations
        ],
    )

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uq_booking_customer_idempotency_key", ["customer_id", "idempotency_key"]
        )
        batch_op.add_column(sa.Column("departure_seats_reserved", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("points_awarded", sa.Numeric(20, 4), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("points_processed", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("points_amount_per_point", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("points_configuration_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("points_reversed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_bookings_points_configuration_id_tour_point_configurations",
            "tour_point_configurations",
            ["points_configuration_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.alter_column("points_processed", server_default=sa.false())

    op.create_table(
        "tour_point_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("package_id", sa.Uuid(), nullable=True),
        sa.Column("configuration_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("points", sa.Numeric(20, 4), nullable=False),
        sa.Column("balance_before", sa.Numeric(20, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount_per_point", sa.Numeric(12, 2), nullable=True),
        sa.Column("booking_code", sa.String(length=20), nullable=True),
        sa.Column("tour_title", sa.String(length=200), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["package_id"], ["tour_packages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["configuration_id"], ["tour_point_configurations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "transaction_type", name="uq_tour_point_booking_event"),
    )
    op.create_index("ix_tour_point_transactions_account_id", "tour_point_transactions", ["account_id"])
    op.create_index("ix_tour_point_transactions_booking_id", "tour_point_transactions", ["booking_id"])
    op.create_index("ix_tour_point_transactions_package_id", "tour_point_transactions", ["package_id"])
    op.create_index(
        "ix_tour_point_transactions_account_created",
        "tour_point_transactions",
        ["account_id", "created_at"],
    )
    op.create_index("ix_tour_point_transactions_created_at", "tour_point_transactions", ["created_at"])


def downgrade() -> None:
    op.drop_table("tour_point_transactions")
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_constraint(
            "fk_bookings_points_configuration_id_tour_point_configurations", type_="foreignkey"
        )
        batch_op.drop_column("points_reversed_at")
        batch_op.drop_column("points_configuration_id")
        batch_op.drop_column("points_amount_per_point")
        batch_op.drop_column("points_processed")
        batch_op.drop_column("points_awarded")
        batch_op.drop_column("departure_seats_reserved")
        batch_op.drop_constraint("uq_booking_customer_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
    op.drop_index("ix_tour_point_configuration_history_tour_type", table_name="tour_point_configuration_history")
    op.drop_index(
        "ix_tour_point_configuration_history_configuration_id", table_name="tour_point_configuration_history"
    )
    op.drop_table("tour_point_configuration_history")
    op.drop_table("tour_point_configurations")
    op.drop_column("accounts", "points_balance")
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.drop_constraint("fk_quotations_departure_id_tour_departures", type_="foreignkey")
        batch_op.drop_index("ix_quotations_departure_id")
        batch_op.drop_column("departure_id")
