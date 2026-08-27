import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity
from datetime import datetime


class TourWishlist(UUIDEntity):
    __tablename__ = "tour_wishlists"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "package_id",
            name="uq_tour_wishlist_customer_package",
        ),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "tour_packages.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

# ── Relationships ───────────────────────────────────────────────────

    customer = relationship(
        "Customer",
        back_populates="tour_wishlists",
    )

    package = relationship(
        "TourPackage",
        back_populates="wishlists",
    )