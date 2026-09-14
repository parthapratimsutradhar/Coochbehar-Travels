"""merge migration heads

Revision ID: 43e002b7fd74
Revises: 6e1f2a3b4c5d, a50c4f75b187
Create Date: 2026-09-14 13:50:33.406750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43e002b7fd74'
down_revision: Union[str, Sequence[str], None] = ('6e1f2a3b4c5d', 'a50c4f75b187')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
