import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveUUIDEntity
    

class TourOfferPackage(ActiveUUIDEntity):
    __tablename__ = "tour_offer_packages"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tour_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tour_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
# ── Relationships ───────────────────────────────────────────────────────

    offer = relationship(
        "TourOffer",
        back_populates="package_links",
    )

    variant = relationship(
        "TourVariant",
        back_populates="offer_links",
    )