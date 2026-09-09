

from decimal import Decimal
import uuid

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDEntity


class VendorPayment(UUIDEntity):
    __tablename__ = "vendor_payments"

    booking_cost_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking_costs.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )
    due_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )