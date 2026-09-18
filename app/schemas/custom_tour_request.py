from datetime import date, datetime
from uuid import UUID
from typing import Literal
from app.core.enums import EnquiryChannel, EnquiryType, VehicleType, MealPlan
from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase


class CustomTourRequestBase(SchemaBase):
    name: str = Field(..., max_length=100)
    mobile: str = Field(..., max_length=20)
    destination_id: UUID | None = None
    destination: str = Field(..., max_length=150)
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    senior_count: int | None = Field(default=None, ge=0)
    room_count: int | None = Field(default=None, ge=0)
    pax_no: int | None = Field(default=4, ge=1)
    no_room: int | None = Field(default=2, ge=1)
    vehicle_type: str | None = Field(default=None, max_length=50)
    meal_plan: str | None = Field(default=None, max_length=50)
    special_requirements: str | None = None


class CustomTourRequestCreate(SchemaBase):
    name: str = Field(..., max_length=100)
    mobile: str = Field(..., max_length=20)
    email: str | None = Field(default=None, max_length=255)
    destination_id: UUID | None = None
    destination: str = Field(..., max_length=150)
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)
    adult_count: int | None = None
    child_count: int | None = None
    senior_count: int | None = None
    room_count: int | None = None
    pax_no: int | None = 4
    no_room: int | None = 2
    vehicle_type: VehicleType | str | None = None
    meal_plan: MealPlan | str | None = None
    special_requirements: str | None = None
    enquiry_type: EnquiryType | None = None
    channel: Literal[EnquiryChannel.WEBSITE, EnquiryChannel.APP] = EnquiryChannel.WEBSITE
    visitor_id: UUID | None = None
    customer_id: UUID | None = None


class CustomTourRequestResponse(CustomTourRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_code: str
    destination_id: UUID | None = None
    enquiry_id: UUID | None = None
    visitor_id: UUID | None = None
    customer_id: UUID | None = None
    status: str = "NEW"
    created_at: datetime
    updated_at: datetime
