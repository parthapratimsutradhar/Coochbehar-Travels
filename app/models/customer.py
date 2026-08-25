from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import LeadSource
from app.models.base import BaseEntity


class Customer(BaseEntity):
    __tablename__ = "customers"

    customer_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
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

    profile_pic: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, name="lead_source"),
        nullable=False,
        default=LeadSource.WEBSITE,
    )

    is_imported: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

# ── Relationships ───────────────────────────────────────────────────────
    visitors = relationship("Visitor", back_populates="customer")
    enquiries = relationship("Enquiry", back_populates="customer")
    leads = relationship("Lead", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")
    auth_sessions = relationship("AuthSession", back_populates="customer", cascade="all, delete-orphan")
    tours = relationship("CustomerTour", back_populates="customer")
    tour_wishlists = relationship("TourWishlist", back_populates="customer", cascade="all, delete-orphan")