"""Enforce one default tour variant per package.

Revision ID: d7e8f9a0b1c2
Revises: f4a5b6c7d8e9
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH ranked_defaults AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY package_id
                           ORDER BY created_at ASC, id ASC
                       ) AS row_num
                FROM tour_variants
                WHERE is_default = true
            )
            UPDATE tour_variants
            SET is_default = false
            WHERE id IN (
                SELECT id
                FROM ranked_defaults
                WHERE row_num > 1
            )
            """
        )
    )
    op.create_index(
        "uq_tour_variants_single_default_per_package",
        "tour_variants",
        ["package_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
        sqlite_where=sa.text("is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_tour_variants_single_default_per_package",
        table_name="tour_variants",
    )