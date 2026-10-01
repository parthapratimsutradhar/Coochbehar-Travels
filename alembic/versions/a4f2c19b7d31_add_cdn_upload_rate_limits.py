"""add shared CDN upload rate limits

Revision ID: a4f2c19b7d31
Revises: 8767edd7015c
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f2c19b7d31"
down_revision: Union[str, Sequence[str], None] = "8767edd7015c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cdn_upload_rate_limits",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("bucket_key", "window_start"),
    )
    op.create_index(
        "ix_cdn_upload_rate_limits_window_start",
        "cdn_upload_rate_limits",
        ["window_start"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cdn_upload_rate_limits_window_start",
        table_name="cdn_upload_rate_limits",
    )
    op.drop_table("cdn_upload_rate_limits")