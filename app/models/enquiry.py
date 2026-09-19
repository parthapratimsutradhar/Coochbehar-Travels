import uuid
from sqlalchemy import Enum, ForeignKey, String, Text, Date, Integer
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType, MealPlan
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
        ForeignKey("accounts.id", ondelete="SET NULL"),
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

    enquirer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    hotel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("hotels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id"),
        nullable=True,
        index=True,
    )

    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    travel_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    travel_duration_day: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    travel_duration_night: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    adult_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    child_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    senior_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    room_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    vehicle_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    meal_plan: Mapped[MealPlan | None] = mapped_column(
        Enum(MealPlan, name="meal_plan"),
        nullable=True
    )

    budget_min: Mapped[float | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    budget_max: Mapped[float | None] = mapped_column(
        Integer,
        nullable=True
    )

    special_requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

# ── Relationships ───────────────────────────────────────────────────────
    visitor = relationship(
        "Visitor",
        back_populates="enquiries"
    )

    customer = relationship(
        "Account",
        back_populates="enquiries"
    )

    package = relationship(
        "TourPackage",
        back_populates="enquiries"
    )

    variant = relationship(
        "TourVariant",
        back_populates="enquiries"
    )

    destination_ref = relationship(
        "Destination",
        foreign_keys=[destination_id],
        back_populates="enquiries",
    )

    hotel = relationship(
        "Hotel",
        foreign_keys=[hotel_id],
        back_populates="enquiries",
    )

    vehicle = relationship(
        "Vehicle",
        foreign_keys=[vehicle_id],
        back_populates="enquiries",
    )

    financial_transactions = relationship(
        "FinancialTransaction",
        back_populates="enquiry",
    )
    
    lead = relationship(
        "Lead",
        back_populates="enquiry",
        uselist=False
    )

    booking = relationship(
        "Booking",
        back_populates="enquiry",
        uselist=False
    )

    quotations = relationship(
        "Quotation",
        back_populates="enquiry"
    )