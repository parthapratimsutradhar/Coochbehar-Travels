"""Remove legacy document and review codes.

Revision ID: d6e7f8a9b0c1
Revises: c9933570f2e0
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c9933570f2e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("documents", "document_code")
    op.drop_column("reviews", "review_code")


def downgrade() -> None:
    op.add_column("documents", sa.Column("document_code", sa.String(30), nullable=True))
    op.create_index("ix_documents_document_code", "documents", ["document_code"], unique=True)
    op.add_column("reviews", sa.Column("review_code", sa.String(20), nullable=True))
    op.create_index("ix_reviews_review_code", "reviews", ["review_code"], unique=True)
