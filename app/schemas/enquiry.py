from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID
from pydantic import AliasChoices, AliasPath, Field, ConfigDict, model_validator
from app.schemas.base import SchemaBase
from app.schemas.lead import LeadSummaryResponse
from app.core.enums import (
    EnquiryChannel,
    EnquiryStatus,
    EnquiryType,
    HotelCategory,
    MealPlan,
    RoomType,
    VehicleType,
)


class EnquiryBase(SchemaBase):
    enquiry_type: EnquiryType = EnquiryType.FIXED_TOUR
    channel: EnquiryChannel
    package_id: UUID | None = None
    variant_id: UUID | None = None
    message: str | None = None


class EnquiryCreate(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "enquiry_type": "FIXED_TOUR",
                    "channel": "WEBSITE",
                    "name": "Asha Roy",
                    "mobile": "+919876543210",
                    "email": "asha@example.com",
                    "destination_id": "c4e91a73-8b26-4d5f-a9c1-7e3b62d84510",
                    "travel_date": "2026-12-10",
                    "travel_duration_day": 5,
                    "travel_duration_night": 4,
                    "adult_count": 2,
                    "child_count": 1,
                    "senior_count": 0,
                    "room_count": 1,
                    "meal_plan": "ANY",
                    "budget_min": 25000,
                    "budget_max": 40000,
                    "special_requirements": "Vegetarian meals preferred.",
                },
                {
                    "enquiry_type": "CUSTOM_TOUR",
                    "channel": "WHATSAPP",
                    "name": "Rahul Sen",
                    "mobile": "+919876543211",
                    "destination_id": "c4e91a73-8b26-4d5f-a9c1-7e3b62d84510",
                    "travel_date": "2026-12-20",
                    "travel_duration_day": 4,
                    "travel_duration_night": 3,
                    "adult_count": 2,
                    "message": "Please suggest a relaxed itinerary.",
                    "special_requirements": "Prefer a private vehicle.",
                }
            ]
        }
    )

    enquiry_type: EnquiryType = Field(
        default=EnquiryType.FIXED_TOUR,
        description="Type of trip requested: fixed tour or custom tour.",
    )
    visitor_id: UUID | None = Field(default=None, description="Optional visitor UUID for an anonymous enquiry.")
    customer_id: UUID | None = Field(
        default=None,
        description="Optional customer UUID supplied with the request; mobile/email are used to resolve an account.",
    )
    package_id: UUID | None = Field(default=None, description="Tour package UUID, when the enquiry is for a package.")
    variant_id: UUID | None = Field(default=None, description="Tour variant UUID, when applicable.")
    destination_id: UUID | None = Field(default=None, description="Destination UUID requested by the traveller.")
    channel: EnquiryChannel = Field(
        default=EnquiryChannel.WEBSITE,
        description="Channel through which the enquiry was received.",
    )
    message: str | None = Field(default=None, description="Free-form message submitted with the enquiry.")
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Name of the person making the enquiry.",
    )
    mobile: str | None = Field(
        default=None,
        max_length=20,
        validation_alias=AliasChoices("phone", "mobile"),
        description="Contact phone number. The request accepts either `mobile` or `phone`.",
    )
    email: str | None = Field(
        default=None,
        max_length=255,
        description="Contact email address. A matching account may be linked to the enquiry.",
    )
    travel_date: date | None = Field(default=None, description="Requested travel start date (YYYY-MM-DD).")
    travel_duration_day: int | None = Field(default=None, ge=0, description="Trip duration in days; must be non-negative.")
    travel_duration_night: int | None = Field(default=None, ge=0, description="Trip duration in nights; must be non-negative.")
    adult_count: int | None = Field(default=None, ge=0, description="Number of adult travellers.")
    child_count: int | None = Field(default=None, ge=0, description="Number of child travellers.")
    senior_count: int | None = Field(default=None, ge=0, description="Number of senior travellers.")
    hotel_category: HotelCategory | None = Field(default=None, description="Preferred hotel category.")
    room_type: RoomType | None = Field(default=None, description="Preferred room configuration.")
    vehicle_type: VehicleType | None = Field(default=None, description="Preferred vehicle type.")
    room_count: int | None = Field(default=None, ge=0, description="Number of rooms requested.")
    vehicle_count: int | None = Field(default=None, ge=0, description="Number of vehicles requested.")
    budget_min: float | None = Field(default=None, ge=0, description="Minimum trip budget; must be non-negative.")
    budget_max: float | None = Field(default=None, ge=0, description="Maximum trip budget; must be non-negative.")
    special_requirements: str | None = Field(
        default=None,
        description="Additional traveller, accessibility, or trip requirements.",
    )
    meal_plan: MealPlan | None = Field(default=None, description="Preferred meal plan.")

    @model_validator(mode="before")
    @classmethod
    def unwrap_data_envelope(cls, data):
        if isinstance(data, Mapping) and set(data) == {"data"}:
            return data["data"]
        return data



class EnquiryUpdate(SchemaBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "IN_PROGRESS"},
                {"message": "Customer requested a call after 6 PM."},
            ]
        }
    )

    status: EnquiryStatus | None = Field(
        default=None,
        description="New enquiry status. Omit this field to keep the current status.",
    )
    message: str | None = Field(
        default=None,
        description="Updated enquiry message. Omit this field to keep the current message.",
    )


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
    hotel_category: HotelCategory | None = None
    room_type: RoomType | None = None
    vehicle_type: VehicleType | None = None
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


class EnquiryForQuotationResponse(EnquiryResponse):
    lead: LeadSummaryResponse | None = Field(default=None, exclude=True)


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
    hotel_category: HotelCategory | None = None
    room_type: RoomType | None = None
    vehicle_type: VehicleType | None = None
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
