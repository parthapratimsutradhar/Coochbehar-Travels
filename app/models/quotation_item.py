import uuid

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.core.enums import QuotationItemType
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.quotation import Quotation


class QuotationItem(BaseEntity):
    """
    Individual commercial item within a quotation.

    Examples:
        Hotel
        Transport
        Flight
        Train
        Meal
        Activity
        Guide
        Permit
        Transfer
        Other
    """

    __tablename__ = "quotation_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_quotation_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_quotation_item_unit_price_non_negative",
        ),
        CheckConstraint(
            "total_price >= 0",
            name="ck_quotation_item_total_price_non_negative",
        ),
    )

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "quotations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    item_type: Mapped[QuotationItemType] = mapped_column(
        Enum(
            QuotationItemType,
            name="quotation_item_type",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    quotation: Mapped["Quotation"] = relationship(
        "Quotation",
        back_populates="items",
    )