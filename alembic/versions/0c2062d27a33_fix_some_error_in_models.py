"""
fix some error in models

Revision ID: 0c2062d27a33
Revises: 762d5127acc8
Create Date: 2026-08-25 21:12:57.857589
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0c2062d27a33"
down_revision: Union[str, Sequence[str], None] = "762d5127acc8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # auth_sessions.actor_type
    # Convert VARCHAR -> PostgreSQL ENUM.
    # ------------------------------------------------------------------

    actor_type_enum = postgresql.ENUM(
        "USER",
        "ADMIN",
        "STAFF",
        "CUSTOMER",
        name="actor_type",
    )

    # PostgreSQL enum type must exist before the column can use it.
    actor_type_enum.create(
        op.get_bind(),
        checkfirst=True,
    )

    # Remove the old VARCHAR default first.
    op.alter_column(
        "auth_sessions",
        "actor_type",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
        existing_nullable=False,
    )

    # Convert existing VARCHAR values to the PostgreSQL enum.
    op.execute(
        """
        ALTER TABLE auth_sessions
        ALTER COLUMN actor_type
        TYPE actor_type
        USING actor_type::actor_type
        """
    )

    # Restore the default using the enum type.
    op.alter_column(
        "auth_sessions",
        "actor_type",
        existing_type=actor_type_enum,
        server_default=sa.text("'USER'::actor_type"),
        existing_nullable=False,
    )

    # ------------------------------------------------------------------
    # customer_tours.enquiry_id
    # Change normal index -> unique index.
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_customer_tours_enquiry_id"),
        table_name="customer_tours",
    )

    op.create_index(
        op.f("ix_customer_tours_enquiry_id"),
        "customer_tours",
        ["enquiry_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # tour_details.variant_id
    # Create unique index because this is a one-to-one relationship.
    # ------------------------------------------------------------------

    op.create_index(
        op.f("ix_tour_details_variant_id"),
        "tour_details",
        ["variant_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ------------------------------------------------------------------
    # tour_details.variant_id
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_tour_details_variant_id"),
        table_name="tour_details",
    )

    # ------------------------------------------------------------------
    # customer_tours.enquiry_id
    # Change unique index -> normal index.
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_customer_tours_enquiry_id"),
        table_name="customer_tours",
    )

    op.create_index(
        op.f("ix_customer_tours_enquiry_id"),
        "customer_tours",
        ["enquiry_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # auth_sessions.actor_type
    # Convert PostgreSQL ENUM -> VARCHAR.
    # ------------------------------------------------------------------

    actor_type_enum = postgresql.ENUM(
        "USER",
        "ADMIN",
        "STAFF",
        "CUSTOMER",
        name="actor_type",
    )

    # Remove enum-based default before changing the column type.
    op.alter_column(
        "auth_sessions",
        "actor_type",
        existing_type=actor_type_enum,
        server_default=None,
        existing_nullable=False,
    )

    # Convert enum values back to VARCHAR.
    op.execute(
        """
        ALTER TABLE auth_sessions
        ALTER COLUMN actor_type
        TYPE VARCHAR(20)
        USING actor_type::text
        """
    )

    # Restore the original VARCHAR default.
    op.alter_column(
        "auth_sessions",
        "actor_type",
        existing_type=sa.VARCHAR(length=20),
        server_default=sa.text("'USER'::character varying"),
        existing_nullable=False,
    )

    # Remove the PostgreSQL enum type.
    actor_type_enum.drop(
        op.get_bind(),
        checkfirst=True,
    )