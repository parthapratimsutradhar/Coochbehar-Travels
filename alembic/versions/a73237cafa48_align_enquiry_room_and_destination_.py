"""align enquiry room and destination fields

Revision ID: a73237cafa48
Revises: 7a1b2c3d4e5f
Create Date: 2026-09-18 21:05:09.653290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a73237cafa48'
down_revision: Union[str, Sequence[str], None] = '7a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'enquiries',
        'room_id',
        new_column_name='hotel_id',
        existing_type=sa.UUID(),
        existing_nullable=True,
    )
    op.create_index(op.f('ix_enquiries_hotel_id'), 'enquiries', ['hotel_id'], unique=False)
    op.create_index(op.f('ix_enquiries_vehicle_id'), 'enquiries', ['vehicle_id'], unique=False)
    op.drop_constraint(op.f('enquiries_room_id_fkey'), 'enquiries', type_='foreignkey')
    op.create_foreign_key(None, 'enquiries', 'rooms', ['hotel_id'], ['id'])
    op.drop_column('enquiries', 'destination')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('enquiries', sa.Column('destination', sa.VARCHAR(length=150), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'enquiries', type_='foreignkey')
    op.alter_column(
        'enquiries',
        'hotel_id',
        new_column_name='room_id',
        existing_type=sa.UUID(),
        existing_nullable=True,
    )
    op.create_foreign_key(op.f('enquiries_room_id_fkey'), 'enquiries', 'rooms', ['room_id'], ['id'])
    op.drop_index(op.f('ix_enquiries_vehicle_id'), table_name='enquiries')
    op.drop_index(op.f('ix_enquiries_hotel_id'), table_name='enquiries')
