from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, EmailStr, Field, AliasChoices
from app.core.enums import BookingSource, BookingStatus, PaymentMethod
from app.schemas.base import SchemaBase
from app.schemas.quotation import (
    QuotationHotelCreate,
    QuotationHotelResponse,
    QuotationItineraryCreate,
    QuotationItineraryResponse,
    QuotationItemCreate,
    QuotationVehicleCreate,
    QuotationVehicleResponse,
)


class BookingTravelerBase(SchemaBase):
    full_name: str = Field(..., min_length=1, max_length=100)
    traveler_type: str | None = Field(default=None, max_length=20)
    gender: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    mobile: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    relationship_to_customer: str | None = Field(default=None, max_length=30)
    is_primary: bool = False


class BookingTravelerCreate(BookingTravelerBase):
    pass


class BookingTravelerUpdate(SchemaBase):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    mobile: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    relationship_to_customer: str | None = Field(default=None, max_length=30)
    is_primary: bool | None = None


class BookingTravelerResponse(BookingTravelerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID


class BookingStatusHistoryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    from_status: str | None = Field(default=None, validation_alias=AliasChoices("from_status", "previous_status"))
    to_status: str = Field(validation_alias=AliasChoices("to_status", "new_status", "status"))
    reason: str | None = Field(default=None, validation_alias=AliasChoices("reason", "notes"))
    changed_at: datetime | None = None
    created_at: datetime | None = Field(default=None, validation_alias=AliasChoices("created_at", "changed_at"))


class OfflineBookingCreate(SchemaBase):
    """Staff manual offline booking creation per whatreq.md specification."""
    customer_id: UUID | None = None
    enquiry_id: UUID | None = None
    quotation_id: UUID | None = None
    customer_name: str = Field(..., min_length=1, max_length=100)
    mobile: str = Field(..., min_length=3, max_length=20)
    email: str | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    departure_id: UUID | None = None
    travel_date: date | None = None
    adult_count: int = Field(default=1, ge=0)
    child_count: int = Field(default=0, ge=0)
    senior_count: int = Field(default=0, ge=0)
    rooms: int | None = 1
    hotel: str | None = None
    transport: str | None = None
    total_selling_price: Decimal = Field(..., ge=0)
    advance_received: Decimal = Field(default=Decimal(0), ge=0)
    payment_mode: PaymentMethod = PaymentMethod.CASH
    sales_account_id: UUID | None = None
    source: BookingSource = BookingSource.OFFLINE
    special_notes: str | None = None
    travellers: list[BookingTravelerCreate] = Field(default_factory=list)
    items: list[QuotationItemCreate] = Field(default_factory=list)
    costs: list[QuotationItemCreate] | None = None
    hotels: list[QuotationHotelCreate] = Field(default_factory=list)
    vehicles: list[QuotationVehicleCreate] = Field(default_factory=list)
    itinerary: list[QuotationItineraryCreate] = Field(default_factory=list)


class OnlineBookingCreate(SchemaBase):
    enquiry_id: UUID | None = None
    quotation_id: UUID | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    departure_id: UUID | None = None
    adult_count: int = Field(default=1, ge=0)
    child_count: int = Field(default=0, ge=0)
    senior_count: int = Field(default=0, ge=0)
    notes: str | None = None
    source: BookingSource = BookingSource.WEBSITE
    travellers: list[BookingTravelerCreate] = Field(default_factory=list)


class BookingUpdate(SchemaBase):
    status: BookingStatus | None = None
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    senior_count: int | None = Field(default=None, ge=0)
    subtotal: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    total_amount: Decimal | None = Field(default=None, ge=0)
    offer_id: UUID | None = None
    notes: str | None = None


class BookingStatusUpdate(SchemaBase):
    status: BookingStatus
    reason: str | None = None


class BookingEmailRequest(SchemaBase):
    recipient_email: EmailStr


class BookingResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_code: str
    customer_id: UUID
    enquiry_id: UUID | None
    package_id: UUID | None
    variant_id: UUID | None
    departure_id: UUID | None
    quotation_id: UUID | None
    offer_id: UUID | None = None
    booking_type: str
    source: BookingSource
    sales_account_id: UUID | None
    status: BookingStatus
    adult_count: int
    child_count: int
    senior_count: int
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class BookingTripItemResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    item_type: str
    name: str
    description: str | None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    hotel: QuotationHotelResponse | None = None
    vehicle: QuotationVehicleResponse | None = None


class BookingDetailResponse(BookingResponse):
    travellers: list[BookingTravelerResponse] = Field(default_factory=list)
    items: list[BookingTripItemResponse] = Field(default_factory=list)
    itinerary: list[QuotationItineraryResponse] = Field(default_factory=list)
    status_history: list[BookingStatusHistoryResponse] = Field(default_factory=list)
    customer_name: str | None = None
    customer_mobile: str | None = None
    gross_profit: Decimal | None = None
    profit_margin: float | None = None
