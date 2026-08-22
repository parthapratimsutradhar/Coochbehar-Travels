"""restore lead activity relationship

Revision ID: d4e5f6a7b8c9
Revises: f40d84aaf6f0
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "f40d84aaf6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restore the lead link required by the LeadActivity ORM model."""
    op.add_column(
        "lead_activities",
        sa.Column("lead_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "lead_activities_lead_id_fkey",
        "lead_activities",
        "leads",
        ["lead_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_lead_activities_lead_id",
        "lead_activities",
        ["lead_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the restored lead link."""
    op.drop_index("ix_lead_activities_lead_id", table_name="lead_activities")
    op.drop_constraint(
        "lead_activities_lead_id_fkey",
        "lead_activities",
        type_="foreignkey",
    )
    op.drop_column("lead_activities", "lead_id")
