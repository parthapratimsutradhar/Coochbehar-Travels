"""add rule regulations

Revision ID: d18c4a7e92bf
Revises: c9e41b7a2d60
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d18c4a7e92bf"
down_revision: Union[str, Sequence[str], None] = "c9e41b7a2d60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_regulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_title", sa.String(length=255), nullable=False),
        sa.Column("regulations", sa.JSON(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rule_regulations_type", "rule_regulations", ["type"])


def downgrade() -> None:
    op.drop_index("ix_rule_regulations_type", table_name="rule_regulations")
    op.drop_table("rule_regulations")