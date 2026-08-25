"""split enquiry travel duration into days and nights

Revision ID: 5e6f7a8b9c0d
Revises: 4b03ed15085c
Create Date: 2026-08-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, Sequence[str], None] = "4b03ed15085c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the legacy string duration with separate day and night values."""
    op.add_column("enquiries", sa.Column("travel_duration_day", sa.Integer(), nullable=True))
    op.add_column("enquiries", sa.Column("travel_duration_night", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE enquiries
            SET travel_duration_day = NULLIF(
                    substring(travel_duration FROM '(\\d+)\\s*day'), ''
                )::integer,
                travel_duration_night = NULLIF(
                    substring(travel_duration FROM '(\\d+)\\s*night'), ''
                )::integer
            WHERE travel_duration IS NOT NULL
            """
        )
    )
    op.drop_column("enquiries", "travel_duration")


def downgrade() -> None:
    """Restore the legacy combined string duration."""
    op.add_column("enquiries", sa.Column("travel_duration", sa.String(length=50), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE enquiries
            SET travel_duration = CASE
                WHEN travel_duration_day IS NOT NULL AND travel_duration_night IS NOT NULL
                    THEN travel_duration_day || ' days, ' || travel_duration_night || ' nights'
                WHEN travel_duration_day IS NOT NULL
                    THEN travel_duration_day || ' days'
                WHEN travel_duration_night IS NOT NULL
                    THEN travel_duration_night || ' nights'
                ELSE NULL
            END
            """
        )
    )
    op.drop_column("enquiries", "travel_duration_night")
    op.drop_column("enquiries", "travel_duration_day")