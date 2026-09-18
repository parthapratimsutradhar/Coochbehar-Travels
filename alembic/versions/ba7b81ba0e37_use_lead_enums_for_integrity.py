"""use lead enums for integrity

Revision ID: ba7b81ba0e37
Revises: 931eb5ce3f0a
Create Date: 2026-09-18 22:23:16.761545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ba7b81ba0e37'
down_revision: Union[str, Sequence[str], None] = '931eb5ce3f0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    lead_activity_type = postgresql.ENUM(
        'CALL', 'WHATSAPP', 'EMAIL', 'NOTE', 'FOLLOW_UP',
        'CUSTOMER_REQUEST', 'QUOTE_SENT', 'QUOTE_UPDATED',
        'STATUS_CHANGED', 'BOOKING_CREATED',
        name='lead_activity_type',
    )
    lead_lost_reason = postgresql.ENUM(
        'PRICE_TOO_HIGH', 'BUDGET_ISSUE', 'TRAVEL_CANCELLED',
        'CHANGED_DESTINATION', 'BOOKED_ELSEWHERE', 'NO_RESPONSE',
        'DATES_UNAVAILABLE', 'NOT_INTERESTED', 'DUPLICATE', 'OTHER',
        name='lead_lost_reason',
    )
    bind = op.get_bind()
    lead_activity_type.create(bind, checkfirst=True)
    lead_lost_reason.create(bind, checkfirst=True)
    op.alter_column('lead_activities', 'activity_type',
               existing_type=sa.VARCHAR(length=50),
               type_=lead_activity_type,
               existing_nullable=False,
               postgresql_using='activity_type::text::lead_activity_type')
    op.alter_column('leads', 'lost_reason',
               existing_type=sa.VARCHAR(length=50),
               type_=lead_lost_reason,
               existing_nullable=True,
               postgresql_using='lost_reason::text::lead_lost_reason')


def downgrade() -> None:
    """Downgrade schema."""
    lead_activity_type = postgresql.ENUM(name='lead_activity_type')
    lead_lost_reason = postgresql.ENUM(name='lead_lost_reason')
    op.alter_column('leads', 'lost_reason',
               existing_type=lead_lost_reason,
               type_=sa.VARCHAR(length=50),
               existing_nullable=True,
               postgresql_using='lost_reason::text')
    op.alter_column('lead_activities', 'activity_type',
               existing_type=lead_activity_type,
               type_=sa.VARCHAR(length=50),
               existing_nullable=False,
               postgresql_using='activity_type::text')
    lead_lost_reason.drop(op.get_bind(), checkfirst=True)
    lead_activity_type.drop(op.get_bind(), checkfirst=True)
