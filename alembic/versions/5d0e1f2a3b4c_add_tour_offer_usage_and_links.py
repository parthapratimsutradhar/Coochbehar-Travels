"""add tour offer usage tracking and booking links

Revision ID: 5d0e1f2a3b4c
Revises: 4cb010bd1860
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5d0e1f2a3b4c"
down_revision: Union[str, Sequence[str], None] = "4cb010bd1860"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE offer_status ADD VALUE IF NOT EXISTS 'PAUSED'"
    )

    op.drop_column("tour_offers", "is_stackable")

    op.add_column(
        "bookings",
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_bookings_offer_id", "bookings", ["offer_id"])
    op.create_foreign_key(
        "fk_bookings_offer_id_tour_offers",
        "bookings",
        "tour_offers",
        ["offer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "quotations",
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_quotations_offer_id", "quotations", ["offer_id"])
    op.create_foreign_key(
        "fk_quotations_offer_id_tour_offers",
        "quotations",
        "tour_offers",
        ["offer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "tour_offer_usages",
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["accounts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"], ["tour_offers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["quotation_id"], ["quotations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tour_offer_usages_offer_id",
        "tour_offer_usages",
        ["offer_id"],
    )
    op.create_index(
        "ix_tour_offer_usages_customer_id",
        "tour_offer_usages",
        ["customer_id"],
    )
    op.create_index(
        "ix_tour_offer_usages_booking_id",
        "tour_offer_usages",
        ["booking_id"],
    )
    op.create_index(
        "ix_tour_offer_usages_quotation_id",
        "tour_offer_usages",
        ["quotation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tour_offer_usages_quotation_id", table_name="tour_offer_usages")
    op.drop_index("ix_tour_offer_usages_booking_id", table_name="tour_offer_usages")
    op.drop_index("ix_tour_offer_usages_customer_id", table_name="tour_offer_usages")
    op.drop_index("ix_tour_offer_usages_offer_id", table_name="tour_offer_usages")
    op.drop_table("tour_offer_usages")

    op.drop_constraint(
        "fk_quotations_offer_id_tour_offers", "quotations", type_="foreignkey"
    )
    op.drop_index("ix_quotations_offer_id", table_name="quotations")
    op.drop_column("quotations", "offer_id")

    op.drop_constraint(
        "fk_bookings_offer_id_tour_offers", "bookings", type_="foreignkey"
    )
    op.drop_index("ix_bookings_offer_id", table_name="bookings")
    op.drop_column("bookings", "offer_id")

    op.add_column(
        "tour_offers",
        sa.Column("is_stackable", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("tour_offers", "is_stackable", server_default=None)
