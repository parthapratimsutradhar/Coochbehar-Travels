"""remove is_active from referral reward configs

Revision ID: 2c7a0f9d3b4d
Revises: 6ba18837d04b
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2c7a0f9d3b4d'
down_revision: Union[str, Sequence[str], None] = '6ba18837d04b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [column["name"] for column in sa.inspect(bind).get_columns("referral_reward_configs")]
    if "is_active" in columns:
        op.drop_column("referral_reward_configs", "is_active")


def downgrade() -> None:
    bind = op.get_bind()
    columns = [column["name"] for column in sa.inspect(bind).get_columns("referral_reward_configs")]
    if "is_active" not in columns:
        op.add_column(
            "referral_reward_configs",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
        op.alter_column("referral_reward_configs", "is_active", server_default=None)
