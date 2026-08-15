import uuid
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import UUID
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

    visitors = relationship("Visitor", back_populates="customer")
    enquiries = relationship("Enquiry", back_populates="customer")
    leads = relationship("Lead", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")