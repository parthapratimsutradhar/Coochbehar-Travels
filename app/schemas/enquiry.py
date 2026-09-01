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
    visitor_id: UUID | None
    customer_id: UUID | None
    status: EnquiryStatus
    enquirer_name: str | None
    enquirer_phone: str | None
    room_id: UUID | None
    vehicle_id: UUID | None
    destination: str | None
    travel_date: date | None
    travel_duration_day: int | None
    travel_duration_night: int | None
    pax_no: int | None
    no_room: int | None
    vehicle_type: str | None
    meal_plan: str | None
    special_requirements: str | None
    created_at: datetime
    updated_at: datetime
