"""add is_active in customer  model

Revision ID: 11e4c56624df
Revises: e0dfa52ae7d1
Create Date: 2026-09-01 13:04:40.397187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11e4c56624df'
down_revision: Union[str, Sequence[str], None] = 'e0dfa52ae7d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "customers",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column(
        "customers",
        "is_active",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("customers", "is_active")
