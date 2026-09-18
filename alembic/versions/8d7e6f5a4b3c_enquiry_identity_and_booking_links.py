"""add enquiry email and relax booking enquiry cardinality"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8d7e6f5a4b3c"
down_revision: Union[str, Sequence[str], None] = "6ba18837d04b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("enquiries", sa.Column("enquirer_email", sa.String(length=255), nullable=True))
    op.create_index("ix_enquiries_enquirer_email", "enquiries", ["enquirer_email"], unique=False)
    op.drop_index("ix_bookings_enquiry_id", table_name="bookings")
    op.create_index("ix_bookings_enquiry_id", "bookings", ["enquiry_id"], unique=False)
    op.alter_column("quotations", "enquiry_id", existing_type=sa.UUID(), nullable=False)
    op.add_column("leads", sa.Column("assigned_account_id", sa.UUID(), nullable=True))
    op.create_index("ix_leads_assigned_account_id", "leads", ["assigned_account_id"], unique=False)
    op.create_foreign_key(
        "fk_leads_assigned_account_id_accounts",
        "leads",
        "accounts",
        ["assigned_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "quotation_status_history",
        sa.Column("quotation_id", sa.UUID(), nullable=False),
        sa.Column("previous_status", postgresql.ENUM("DRAFT", "SENT", "VIEWED", "ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED", name="quotation_status", create_type=False), nullable=True),
        sa.Column("status", postgresql.ENUM("DRAFT", "SENT", "VIEWED", "ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED", name="quotation_status", create_type=False), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_status_history_quotation_id", "quotation_status_history", ["quotation_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_enquiry_id", table_name="bookings")
    op.create_index("ix_bookings_enquiry_id", "bookings", ["enquiry_id"], unique=True)
    op.alter_column("quotations", "enquiry_id", existing_type=sa.UUID(), nullable=True)
    op.drop_index("ix_quotation_status_history_quotation_id", table_name="quotation_status_history")
    op.drop_table("quotation_status_history")
    op.drop_constraint("fk_leads_assigned_account_id_accounts", "leads", type_="foreignkey")
    op.drop_index("ix_leads_assigned_account_id", table_name="leads")
    op.drop_column("leads", "assigned_account_id")
    op.drop_index("ix_enquiries_enquirer_email", table_name="enquiries")
    op.drop_column("enquiries", "enquirer_email")