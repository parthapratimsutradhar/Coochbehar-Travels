
from sqlalchemy import String
from app.models.base import UUIDEntity

from sqlalchemy.orm import Mapped, mapped_column


class Vendor(UUIDEntity):
    """
    Represents a vendor in the system.
    Contains details about the vendor, including contact information and status.
    """
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    contact: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
