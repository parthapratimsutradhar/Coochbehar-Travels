from datetime import date, datetime
from uuid import UUID
from typing import Literal
from app.core.enums import EnquiryChannel, EnquiryType, VehicleType, MealPlan
from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase


class CustomTourRequestBase(SchemaBase):
    name: str = Field(..., max_length=100)
    mobile: str = Field(..., max_length=20)
    destination: str = Field(..., max_length=150)
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)
    pax_no: int = Field(default=4, ge=1)
    no_room: int = Field(default=2, ge=1)
    vehicle_type: str | None = Field(default=None, max_length=50)
    meal_plan: str | None = Field(default=None, max_length=50)
    special_requirements: str | None = None



class CustomTourRequestCreate(SchemaBase):
    name: str = Field(..., max_length=100)
    mobile: str = Field(..., max_length=20)
    destination: str = Field(..., max_length=150)
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)

    pax_no: int = Field(default=4, ge=1)
    no_room: int = Field(default=2, ge=1)

    vehicle_type: VehicleType | None = None
    meal_plan: MealPlan | None = None
    special_requirements: str | None = None
    enquiry_type: Literal[
        EnquiryType.CUSTOM_TOUR,
        EnquiryType.ROOM_REQUEST,
        EnquiryType.VEHICLE_REQUEST,
    ] | None = None
    channel: Literal[EnquiryChannel.WEBSITE, EnquiryChannel.APP] = EnquiryChannel.WEBSITE
    visitor_id: UUID | None = None
    customer_id: UUID | None = None


class CustomTourRequestResponse(CustomTourRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_code: str
    enquiry_id: UUID | None
    visitor_id: UUID | None
    customer_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime
