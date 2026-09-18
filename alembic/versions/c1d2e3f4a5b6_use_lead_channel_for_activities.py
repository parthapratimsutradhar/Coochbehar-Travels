"""use LeadChannel for lead activities

Revision ID: c1d2e3f4a5c7
Revises: ba7b81ba0e37
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c1d2e3f4a5c7"
down_revision: Union[str, Sequence[str], None] = "ba7b81ba0e37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    lead_channel = postgresql.ENUM(
        "WHATSAPP",
        "PHONE",
        "EMAIL",
        "OFFLINE",
        name="lead_channel",
    )
    bind = op.get_bind()
    lead_channel.create(bind, checkfirst=True)
    op.alter_column(
        "lead_activities",
        "channel",
        existing_type=postgresql.ENUM(name="enquiry_channel"),
        type_=lead_channel,
        existing_nullable=False,
        postgresql_using=(
            "CASE WHEN channel::text IN ('WHATSAPP', 'PHONE', 'EMAIL', 'OFFLINE') "
            "THEN channel::text::lead_channel ELSE 'OFFLINE'::lead_channel END"
        ),
    )


def downgrade() -> None:
    enquiry_channel = postgresql.ENUM(name="enquiry_channel")
    op.alter_column(
        "lead_activities",
        "channel",
        existing_type=postgresql.ENUM(name="lead_channel"),
        type_=enquiry_channel,
        existing_nullable=False,
        postgresql_using="channel::text::enquiry_channel",
    )
    postgresql.ENUM(name="lead_channel").drop(op.get_bind(), checkfirst=True)