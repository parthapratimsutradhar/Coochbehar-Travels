"""add tour variant fields

Revision ID: a1b2c3d4e5f6
Revises: 30817af8ec10
Create Date: 2026-08-14 18:29:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '30817af8ec10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tour_variants', sa.Column('key', sa.String(length=50), nullable=True))
    op.add_column('tour_variants', sa.Column('display_order', sa.Integer(), nullable=True))
    op.add_column('tour_variants', sa.Column('badge', sa.String(length=50), nullable=True))
    op.add_column('tour_variants', sa.Column('season_type', sa.String(length=50), nullable=True))
    op.add_column('tour_variants', sa.Column('currency', sa.String(length=10), server_default='INR', nullable=True))
    op.add_column('tour_variants', sa.Column('availability', sa.String(length=20), server_default='AVAILABLE', nullable=True))


def downgrade() -> None:
    op.drop_column('tour_variants', 'availability')
    op.drop_column('tour_variants', 'currency')
    op.drop_column('tour_variants', 'season_type')
    op.drop_column('tour_variants', 'badge')
    op.drop_column('tour_variants', 'display_order')
    op.drop_column('tour_variants', 'key')
