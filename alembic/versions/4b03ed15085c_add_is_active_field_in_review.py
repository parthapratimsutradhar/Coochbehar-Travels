"""add is_active field in review

Revision ID: 4b03ed15085c
Revises: 0c2062d27a33
Create Date: 2026-08-25 22:03:49.967869
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b03ed15085c"
down_revision: Union[str, Sequence[str], None] = "0c2062d27a33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reviews",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    # Remove the database-level default after existing rows
    # have been populated. New records will use the ORM default.
    op.alter_column(
        "reviews",
        "is_active",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("reviews", "is_active")