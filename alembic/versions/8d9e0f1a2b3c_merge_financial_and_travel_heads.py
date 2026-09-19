"""merge financial and travel migration heads

Revision ID: 8d9e0f1a2b3c
Revises: 7c8d9e0f1a2b, f8a9b0c1d2e3
"""

from typing import Sequence, Union

from alembic import op


revision: str = "8d9e0f1a2b3c"
down_revision: Union[str, Sequence[str], None] = ("7c8d9e0f1a2b", "f8a9b0c1d2e3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
