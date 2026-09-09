"""Make account email and mobile unique per role.

Revision ID: c2d3e4f5a6b7
Revises: f16e3fb091a7
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "f16e3fb091a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_index("ix_accounts_mobile", table_name="accounts")
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=False)
    op.create_index("ix_accounts_mobile", "accounts", ["mobile"], unique=False)
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


def downgrade() -> None:
    op.drop_constraint("uq_accounts_email_role", "accounts", type_="unique")
    op.drop_constraint("uq_accounts_mobile_role", "accounts", type_="unique")
    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_index("ix_accounts_mobile", table_name="accounts")
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=True)
    op.create_index("ix_accounts_mobile", "accounts", ["mobile"], unique=True)
