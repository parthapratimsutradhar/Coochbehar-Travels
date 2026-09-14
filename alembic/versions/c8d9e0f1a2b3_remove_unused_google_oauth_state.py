"""remove unused Google OAuth state table

Revision ID: c8d9e0f1a2b3
Revises: bf256a9bdbec
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "bf256a9bdbec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("google_oauth_states")


def downgrade() -> None:
    raise NotImplementedError(
        "The obsolete google_oauth_states table is intentionally not recreated."
    )
