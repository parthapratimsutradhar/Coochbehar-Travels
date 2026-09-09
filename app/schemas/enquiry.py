from datetime import date, datetime
from uuid import UUID
from typing import Literal
from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase
from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType


class EnquiryBase(SchemaBase):
    enquiry_type: EnquiryType = EnquiryType.FIXED_TOUR
    channel: EnquiryChannel
    package_id: UUID | None = None
    variant_id: UUID | None = None
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = None


class EnquiryCreate(SchemaBase):
    package_id: UUID | None = None
    variant_id: UUID | None = None
    channel: Literal[EnquiryChannel.WEBSITE, EnquiryChannel.APP] = EnquiryChannel.WEBSITE
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = None
    name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    visitor_id: UUID | None = None
    customer_id: UUID | None = None


class EnquiryUpdate(SchemaBase):
    status: EnquiryStatus | None = None
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = None


class EnquiryResponse(EnquiryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enquiry_code: str
    visitor_id: UUID | None = None
    customer_id: UUID | None = None
    status: EnquiryStatus
    enquirer_name: str | None = None
    enquirer_phone: str | None = None
    room_id: UUID | None = None
    vehicle_id: UUID | None = None
    destination: str | None = None
    travel_date: date | None = None
    travel_duration_day: int | None = None
    travel_duration_night: int | None = None
    adult_count: int | None = None
    child_count: int | None = None
    senior_count: int | None = None
    room_count: int | None = None
    pax_no: int | None = None
    no_room: int | None = None
    vehicle_type: str | None = None
    meal_plan: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    special_requirements: str | None = None
    created_at: datetime
    updated_at: datetime
