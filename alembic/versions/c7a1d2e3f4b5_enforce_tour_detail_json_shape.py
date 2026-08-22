"""enforce tour detail JSON shape

Revision ID: c7a1d2e3f4b5
Revises: b48b3f038186
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c7a1d2e3f4b5"
down_revision: Union[str, Sequence[str], None] = "b48b3f038186"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Require the top-level JSON values used by the public tour API."""
    op.create_check_constraint(
        "ck_tour_details_banner_json_type",
        "tour_details",
        "jsonb_typeof(banner) IN ('string', 'object')",
    )
    for column in (
        "gallery",
        "highlights",
        "inclusions",
        "exclusions",
        "departures_dates",
        "itinerary",
        "route_stops",
    ):
        op.create_check_constraint(
            f"ck_tour_details_{column}_is_array",
            "tour_details",
            f"jsonb_typeof({column}) = 'array'",
        )


def downgrade() -> None:
    """Remove the JSON shape checks."""
    op.drop_constraint("ck_tour_details_banner_json_type", "tour_details", type_="check")
    for column in (
        "gallery",
        "highlights",
        "inclusions",
        "exclusions",
        "departures_dates",
        "itinerary",
        "route_stops",
    ):
        op.drop_constraint(f"ck_tour_details_{column}_is_array", "tour_details", type_="check")
