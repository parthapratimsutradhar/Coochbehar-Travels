"""add meal plan enum to enquiries

Revision ID: 7a1b2c3d4e5f
Revises: 60633c12b803
Create Date: 2026-09-16

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "60633c12b803"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


meal_plan_enum = postgresql.ENUM(
    "ANY",
    "NONE",
    "CP",
    "MAP",
    "AP",
    name="meal_plan",
)


def upgrade() -> None:
    meal_plan_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "enquiries",
        "meal_plan",
        existing_type=postgresql.VARCHAR(length=50),
        type_=meal_plan_enum,
        existing_nullable=True,
        postgresql_using="meal_plan::meal_plan",
    )


def downgrade() -> None:
    op.alter_column(
        "enquiries",
        "meal_plan",
        existing_type=meal_plan_enum,
        type_=postgresql.VARCHAR(length=50),
        existing_nullable=True,
        postgresql_using="meal_plan::text",
    )
    meal_plan_enum.drop(op.get_bind(), checkfirst=True)
