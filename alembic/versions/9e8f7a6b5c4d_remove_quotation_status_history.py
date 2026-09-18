"""remove unused quotation status history"""

from typing import Sequence, Union

from alembic import op


revision: str = "9e8f7a6b5c4d"
down_revision: Union[str, Sequence[str], None] = "8d7e6f5a4b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_quotation_status_history_quotation_id", table_name="quotation_status_history")
    op.drop_table("quotation_status_history")


def downgrade() -> None:
    pass