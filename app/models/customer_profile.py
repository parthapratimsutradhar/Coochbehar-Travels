import uuid
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy import Boolean, Enum, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import LeadSource,OfferDiscountType
from app.models.base import UUIDEntity

class CustomerProfile(UUIDEntity):
    __tablename__ = "customer_profiles"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    emergency_contact_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    emergency_contact_mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, name="lead_source"),
        nullable=False,
        default=LeadSource.WEBSITE,
    )

    special_discount_type: Mapped[OfferDiscountType] = mapped_column(
        Enum(OfferDiscountType, name="discount_type"),
        nullable=True,
    )
    
    special_discount: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    referral_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
    )

    account = relationship(
        "Account",
        back_populates="customer_profile",
    )