"""remove visitor lead_score

Revision ID: e7b8c9d0e1f2
Revises: 11e4c56624df
Create Date: 2026-09-01 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = '11e4c56624df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — remove lead_score from visitors."""
    op.drop_column('visitors', 'lead_score')


def downgrade() -> None:
    """Downgrade schema — restore lead_score on visitors."""
    op.add_column(
        'visitors',
        sa.Column('lead_score', sa.Integer(), nullable=False, server_default='0'),
    )
    op.alter_column('visitors', 'lead_score', server_default=None)
