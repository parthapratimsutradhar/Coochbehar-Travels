"""create auth_sessions table and add profile_pic to users and customers

Revision ID: c1d2e3f4a5b6
Revises: b6e8231d744e
Create Date: 2026-08-16 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b6e8231d744e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add profile_pic column to users and customers if not present
    op.add_column('users', sa.Column('profile_pic', sa.String(length=500), nullable=True))
    op.add_column('customers', sa.Column('profile_pic', sa.String(length=500), nullable=True))

    # 2. Create auth_sessions table
    op.create_table(
        'auth_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_type', sa.String(length=20), server_default='USER', nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'last_used_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            ['customers.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_auth_sessions_refresh_token_hash'),
        'auth_sessions',
        ['refresh_token_hash'],
        unique=True,
    )
    op.create_index(
        op.f('ix_auth_sessions_user_id'),
        'auth_sessions',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_auth_sessions_customer_id'),
        'auth_sessions',
        ['customer_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_auth_sessions_customer_id'), table_name='auth_sessions')
    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_index(
        op.f('ix_auth_sessions_refresh_token_hash'), table_name='auth_sessions'
    )
    op.drop_table('auth_sessions')
    op.drop_column('customers', 'profile_pic')
    op.drop_column('users', 'profile_pic')
