from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID
from pydantic import AliasChoices, AliasPath, Field, ConfigDict, model_validator
from app.schemas.base import SchemaBase
from app.schemas.lead import LeadSummaryResponse
from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType, MealPlan


class EnquiryBase(SchemaBase):
    enquiry_type: EnquiryType = EnquiryType.FIXED_TOUR
    channel: EnquiryChannel
    package_id: UUID | None = None
    variant_id: UUID | None = None
    message: str | None = None


class EnquiryCreate(SchemaBase):
    enquiry_type: EnquiryType = EnquiryType.FIXED_TOUR
    visitor_id: UUID | None = None
    customer_id: UUID | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    destination_id: UUID | None = None
    channel: EnquiryChannel = EnquiryChannel.WEBSITE
    message: str | None = None
    name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone", "mobile"),
    )
    email: str | None = Field(default=None, max_length=255)
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    senior_count: int | None = Field(default=None, ge=0)
    hotel_id: UUID | None = None
    vehicle_id: UUID | None = None
    room_count: int | None = Field(default=None, ge=0)
    vehicle_count: int | None = Field(default=None, ge=0)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    special_requirements: str | None = None
    meal_plan: MealPlan | None = None

    @model_validator(mode="before")
    @classmethod
    def unwrap_data_envelope(cls, data):
        if isinstance(data, Mapping) and set(data) == {"data"}:
            return data["data"]
        return data



class EnquiryUpdate(SchemaBase):
    status: EnquiryStatus | None = None
    message: str | None = None


class CustomerEnquiryUpdate(SchemaBase):
    package_id: UUID | None = None
    variant_id: UUID | None = None
    destination_id: UUID | None = None
    message: str | None = None
    enquirer_name: str | None = Field(default=None, max_length=100, validation_alias=AliasChoices("name", "enquirer_name"))
    enquirer_phone: str | None = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone", "mobile", "enquirer_phone"),
    )
    enquirer_email: str | None = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("email", "enquirer_email"),
    )
    travel_date: date | None = None
    travel_duration_day: int | None = Field(default=None, ge=0)
    travel_duration_night: int | None = Field(default=None, ge=0)
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    senior_count: int | None = Field(default=None, ge=0)
    hotel_id: UUID | None = None
    vehicle_id: UUID | None = None
    room_count: int | None = Field(default=None, ge=0)
    vehicle_count: int | None = Field(default=None, ge=0)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    special_requirements: str | None = None
    meal_plan: MealPlan | None = None


class EnquiryResponse(EnquiryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enquiry_code: str
    visitor_id: UUID | None = None
    customer_id: UUID | None = None
    destination_id: UUID | None = None
    status: EnquiryStatus
    lead: LeadSummaryResponse | None = None
    enquirer_name: str | None = None
    enquirer_phone: str | None = None
    enquirer_email: str | None = None
    hotel_id: UUID | None = None
    vehicle_id: UUID | None = None
    travel_date: date | None = None
    travel_duration_day: int | None = None
    travel_duration_night: int | None = None
    adult_count: int | None = None
    child_count: int | None = None
    senior_count: int | None = None
    room_count: int | None = None
    vehicle_count: int | None = None
    meal_plan: MealPlan | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    special_requirements: str | None = None
    created_at: datetime
    updated_at: datetime


class CustomerEnquiryResponse(EnquiryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enquiry_code: str
    visitor_id: UUID | None = None
    customer_id: UUID | None = None
    destination_id: UUID | None = None
    destination_name: str | None = Field(
        default=None,
        validation_alias=AliasPath("destination_ref", "name"),
    )
    status: EnquiryStatus
    enquirer_name: str | None = None
    enquirer_phone: str | None = None
    enquirer_email: str | None = None
    hotel_id: UUID | None = None
    hotel_name: str | None = Field(default=None, validation_alias=AliasPath("hotel", "name"))
    vehicle_id: UUID | None = None
    vehicle_name: str | None = Field(default=None, validation_alias=AliasPath("vehicle", "name"))
    vehicle_registration_number: str | None = Field(
        default=None,
        validation_alias=AliasPath("vehicle", "registration_number"),
    )
    travel_date: date | None = None
    travel_duration_day: int | None = None
    travel_duration_night: int | None = None
    adult_count: int | None = None
    child_count: int | None = None
    senior_count: int | None = None
    room_count: int | None = None
    vehicle_count: int | None = None
    meal_plan: MealPlan | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    special_requirements: str | None = None
    created_at: datetime
    updated_at: datetime
