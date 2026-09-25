"""add tour identity fields to quotations

Revision ID: e5f6a7b8c9d0
Revises: b1c2d3e4f5a6
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quotations", sa.Column("package_id", sa.UUID(), nullable=True))
    op.add_column("quotations", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.add_column("quotations", sa.Column("destination_id", sa.UUID(), nullable=True))

    op.create_index("ix_quotations_package_id", "quotations", ["package_id"], unique=False)
    op.create_index("ix_quotations_variant_id", "quotations", ["variant_id"], unique=False)
    op.create_index("ix_quotations_destination_id", "quotations", ["destination_id"], unique=False)

    op.create_foreign_key(
        "fk_quotations_package_id_tour_packages",
        "quotations",
        "tour_packages",
        ["package_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_quotations_variant_id_tour_variants",
        "quotations",
        "tour_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_quotations_destination_id_destinations",
        "quotations",
        "destinations",
        ["destination_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotations_destination_id_destinations", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_variant_id_tour_variants", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_package_id_tour_packages", "quotations", type_="foreignkey")
    op.drop_index("ix_quotations_destination_id", table_name="quotations")
    op.drop_index("ix_quotations_variant_id", table_name="quotations")
    op.drop_index("ix_quotations_package_id", table_name="quotations")
    op.drop_column("quotations", "destination_id")
    op.drop_column("quotations", "variant_id")
    op.drop_column("quotations", "package_id")