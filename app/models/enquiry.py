import uuid
from sqlalchemy import Enum, ForeignKey, String, Text, Date, Integer
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType
from app.models.base import BaseEntity


class Enquiry(BaseEntity):
    __tablename__ = "enquiries"

    enquiry_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    visitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    enquiry_type: Mapped[EnquiryType] = mapped_column(
        Enum(EnquiryType, name="enquiry_type"),
        nullable=False,
    )

    channel: Mapped[EnquiryChannel] = mapped_column(
        Enum(EnquiryChannel, name="enquiry_channel"),
        nullable=False,
    )

    status: Mapped[EnquiryStatus] = mapped_column(
        Enum(EnquiryStatus, name="enquiry_status"),
        nullable=False,
        default=EnquiryStatus.NEW,
        index=True,
    )

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tour_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    enquirer_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    enquirer_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    room_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=True,
    )

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id"),
        nullable=True,
    )

    destination: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    travel_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    travel_duration: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    pax_no: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    no_room: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    vehicle_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    meal_plan: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    special_requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

# ── Relationships ───────────────────────────────────────────────────────
    visitor = relationship("Visitor", back_populates="enquiries")
    customer = relationship("Customer", back_populates="enquiries")
    package = relationship("TourPackage", back_populates="enquiries")
    variant = relationship("TourVariant", back_populates="enquiries")
    lead = relationship("Lead", back_populates="enquiry", uselist=False)
