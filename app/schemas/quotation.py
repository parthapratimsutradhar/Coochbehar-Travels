from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import AliasChoices, ConfigDict, EmailStr, Field, model_validator
from app.core.enums import CostItemType, QuotationStatus, RoomType, VehicleType
from app.schemas.base import SchemaBase


class QuotationItemBase(SchemaBase):
    item_type: CostItemType = CostItemType.OTHER
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal(0), ge=0)
    total_price: Decimal = Field(default=Decimal(0), ge=0)


class QuotationHotelCreate(SchemaBase):
    hotel_id: UUID | None = None
    hotel_name: str = Field(..., min_length=1, max_length=255)
    check_in: datetime
    check_out: datetime
    nights: int = Field(..., ge=1)
    room_count: int = Field(default=1, ge=1)
    room_type: RoomType | None = None


class QuotationHotelResponse(QuotationHotelCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_item_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotationVehicleCreate(SchemaBase):
    vehicle_id: UUID | None = None
    vehicle_name: str = Field(..., min_length=1, max_length=255)
    vehicle_type: VehicleType | None = None
    start_date: datetime
    end_date: datetime
    rental_minutes: int = Field(..., ge=1)
    quantity: int = Field(default=1, ge=1)


class QuotationVehicleResponse(QuotationVehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_item_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotationItineraryCreate(SchemaBase):
    day_number: int = Field(..., ge=1)
    date: datetime | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    overnight_location: str | None = Field(default=None, max_length=255)
    meal_plan: str | None = Field(default=None, max_length=50)
    sort_order: int = Field(default=0, ge=0)


class QuotationItineraryResponse(QuotationItineraryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quotation_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemResponse(QuotationItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quotation_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotationBase(SchemaBase):
    customer_id: UUID | None = None
    enquiry_id: UUID
    package_id: UUID | None = None
    variant_id: UUID | None = None
    destination_id: UUID | None = None
    tour_name: str = Field(..., min_length=1, max_length=255)
    travel_date: datetime | None = None
    return_date: datetime | None = None
    subtotal: Decimal = Field(default=Decimal(0), ge=0)
    discount_amount: Decimal = Field(default=Decimal(0), ge=0)
    tax_amount: Decimal = Field(default=Decimal(0), ge=0)
    total_amount: Decimal = Field(default=Decimal(0), ge=0)
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None
    important_notes: str | None = None
    inclusion: str | None = None
    exclusion: str | None = None


class QuotationCreate(QuotationBase):
    items: list[QuotationItemCreate] = Field(default_factory=list)
    hotels: list[QuotationHotelCreate] = Field(default_factory=list)
    vehicles: list[QuotationVehicleCreate] = Field(default_factory=list)
    itinerary: list[QuotationItineraryCreate] = Field(default_factory=list)


class QuotationVersionCreate(SchemaBase):
    package_id: UUID | None = None
    variant_id: UUID | None = None
    destination_id: UUID | None = None
    tour_name: str | None = Field(default=None, min_length=1, max_length=255)
    travel_date: datetime | None = None
    return_date: datetime | None = None
    subtotal: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    total_amount: Decimal | None = Field(default=None, ge=0)
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None
    important_notes: str | None = None
    inclusion: str | None = None
    exclusion: str | None = None
    items: list[QuotationItemCreate] | None = None
    hotels: list[QuotationHotelCreate] | None = None
    vehicles: list[QuotationVehicleCreate] | None = None
    itinerary: list[QuotationItineraryCreate] | None = None


class QuotationUpdate(SchemaBase):
    customer_id: UUID | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    destination_id: UUID | None = None
    tour_name: str | None = Field(default=None, min_length=1, max_length=255)
    travel_date: datetime | None = None
    return_date: datetime | None = None
    subtotal: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    total_amount: Decimal | None = Field(default=None, ge=0)
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None
    important_notes: str | None = None
    inclusion: str | None = None
    exclusion: str | None = None
    items: list[QuotationItemCreate] | None = None
    hotels: list[QuotationHotelCreate] | None = None
    vehicles: list[QuotationVehicleCreate] | None = None
    itinerary: list[QuotationItineraryCreate] | None = None


class QuotationListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quotation_code: str
    tour_name: str
    travel_date: datetime | None = None
    return_date: datetime | None = None
    total_amount: Decimal = Field(default=Decimal(0), ge=0)
    valid_until: datetime | None = None
    version: int
    status: QuotationStatus


class QuotationCustomerSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mobile: str | None = None
    email: str | None = None
    profile_picture: str | None = Field(
        default=None,
        validation_alias=AliasChoices("profile_picture", "profile_pic"),
    )


class QuotationPackageSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(validation_alias=AliasChoices("name", "title"))
    description: str | None = None


class QuotationVariantSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    banner: dict[str, str | None] | None = None
    season_name: str | None = None


class QuotationDestinationSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class QuotationCreatedBySummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    account_id: UUID = Field(validation_alias=AliasChoices("account_id", "id"))
    name: str
    email: str | None = None
    profile_picture: str | None = Field(
        default=None,
        validation_alias=AliasChoices("profile_picture", "profile_pic"),
    )


class QuotationStatusUpdate(SchemaBase):
    status: QuotationStatus


class QuotationEmailRequest(SchemaBase):
    recipient_email: EmailStr


class QuotationResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    customer: QuotationCustomerSummaryResponse | None = None
    enquiry_id: UUID
    package: QuotationPackageSummaryResponse | None = None
    variant: QuotationVariantSummaryResponse | None = None
    destination: QuotationDestinationSummaryResponse | None = None
    tour_name: str
    travel_date: datetime | None = None
    return_date: datetime | None = None
    subtotal: Decimal = Field(default=Decimal(0), ge=0)
    discount_amount: Decimal = Field(default=Decimal(0), ge=0)
    tax_amount: Decimal = Field(default=Decimal(0), ge=0)
    total_amount: Decimal = Field(default=Decimal(0), ge=0)
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None
    important_notes: str | None = None
    inclusion: str | None = None
    exclusion: str | None = None
    id: UUID
    quotation_code: str
    version: int
    status: QuotationStatus
    created_by: QuotationCreatedBySummaryResponse | None = None
    sent_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    rejected_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemResponse] = Field(default_factory=list)
    hotels: list[QuotationHotelResponse] = Field(default_factory=list)
    vehicles: list[QuotationVehicleResponse] = Field(default_factory=list)
    itinerary: list[QuotationItineraryResponse] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def flatten_trip_details(cls, value):
        if isinstance(value, dict):
            return value
        data = {
            field: getattr(value, field, None)
            for field in cls.model_fields
            if field not in {"items", "hotels", "vehicles", "itinerary", "customer", "package", "variant", "destination", "created_by"}
        }
        data["customer"] = getattr(value, "customer", None)
        data["package"] = getattr(value, "package", None)
        data["variant"] = getattr(value, "variant", None)
        data["destination"] = getattr(value, "destination", None)
        data["created_by"] = getattr(value, "created_by", None)
        items = list(getattr(value, "items", []) or [])
        data["items"] = items
        data["hotels"] = [item.hotel for item in items if getattr(item, "hotel", None)]
        data["vehicles"] = [item.vehicle for item in items if getattr(item, "vehicle", None)]
        data["itinerary"] = list(getattr(value, "itinerary", []) or [])
        return data


class QuotationConvertToBookingRequest(SchemaBase):
    booking_type: str = "PACKAGE"
    notes: str | None = None
