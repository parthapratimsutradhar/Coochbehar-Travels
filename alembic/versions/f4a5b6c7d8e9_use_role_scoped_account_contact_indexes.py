"""Use role-scoped account contact indexes.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_accounts_email_role", "accounts", type_="unique")
    op.drop_constraint("uq_accounts_mobile_role", "accounts", type_="unique")

    op.create_index(
        "uq_active_customer_email",
        "accounts",
        ["email"],
        unique=True,
        postgresql_where=sa.text("role = 'CUSTOMER' AND is_active = true"),
        sqlite_where=sa.text("role = 'CUSTOMER' AND is_active = true"),
    )
    op.create_index(
        "uq_admin_email",
        "accounts",
        ["email"],
        unique=True,
        postgresql_where=sa.text("role = 'ADMIN'"),
        sqlite_where=sa.text("role = 'ADMIN'"),
    )
    op.create_index(
        "uq_staff_email",
        "accounts",
        ["email"],
        unique=True,
        postgresql_where=sa.text("role = 'STAFF'"),
        sqlite_where=sa.text("role = 'STAFF'"),
    )
    op.create_index(
        "uq_active_customer_mobile",
        "accounts",
        ["mobile"],
        unique=True,
        postgresql_where=sa.text("role = 'CUSTOMER' AND is_active = true"),
        sqlite_where=sa.text("role = 'CUSTOMER' AND is_active = true"),
    )
    op.create_index(
        "uq_admin_mobile",
        "accounts",
        ["mobile"],
        unique=True,
        postgresql_where=sa.text("role = 'ADMIN'"),
        sqlite_where=sa.text("role = 'ADMIN'"),
    )
    op.create_index(
        "uq_staff_mobile",
        "accounts",
        ["mobile"],
        unique=True,
        postgresql_where=sa.text("role = 'STAFF'"),
        sqlite_where=sa.text("role = 'STAFF'"),
    )


def downgrade() -> None:
    op.drop_index("uq_staff_mobile", table_name="accounts")
    op.drop_index("uq_admin_mobile", table_name="accounts")
    op.drop_index("uq_active_customer_mobile", table_name="accounts")
    op.drop_index("uq_staff_email", table_name="accounts")
    op.drop_index("uq_admin_email", table_name="accounts")
    op.drop_index("uq_active_customer_email", table_name="accounts")

    op.create_unique_constraint(
        "uq_accounts_email_role",
        "accounts",
        ["email", "role"],
    )
    op.create_unique_constraint(
        "uq_accounts_mobile_role",
        "accounts",
        ["mobile", "role"],
    )