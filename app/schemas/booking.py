from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, EmailStr, Field, AliasChoices, model_validator
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
    tour_offer_id: UUID | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    departure_id: UUID | None = None
    travel_date: date | None = None
    adult_count: int = Field(default=1, ge=0)
    child_count: int = Field(default=0, ge=0)
    senior_count: int = Field(default=0, ge=0)
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


class BookingAccountSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str | None = None
    mobile: str | None = None
    profile_pic: str | None = Field(default=None, validation_alias=AliasChoices("profile_pic", "profile_picture"))


class BookingEnquirySummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    destination_id: UUID | None = None
    destination_name: str | None = None


class BookingPackageSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(validation_alias=AliasChoices("title", "name"))
    season: str | None = Field(default=None, validation_alias=AliasChoices("season_name", "season"))


class BookingVariantSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    banner: dict[str, str | None] | None = None


class BookingDepartureSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    departure_date: date | None = None
    return_date: date | None = None


class BookingOfferSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None


class BookingResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_code: str
    customer: BookingAccountSummaryResponse | None = None
    enquiry: BookingEnquirySummaryResponse | None = None
    package: BookingPackageSummaryResponse | None = None
    variant: BookingVariantSummaryResponse | None = None
    departure: BookingDepartureSummaryResponse | None = None
    booking_type: str
    source: BookingSource
    status: BookingStatus
    total_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal

    @model_validator(mode="before")
    @classmethod
    def normalize_booking_response(cls, value):
        if isinstance(value, dict):
            return value

        if value is None:
            return None

        customer = getattr(value, "customer", None)
        enquiry = getattr(value, "enquiry", None)
        package = getattr(value, "package", None)
        variant = getattr(value, "variant", None)
        departure = getattr(value, "departure", None)

        banner = None
        if variant is not None:
            details = getattr(variant, "details", None)
            raw_banner = getattr(details, "banner", None) if details is not None else None
            if isinstance(raw_banner, dict):
                banner = {
                    "image": raw_banner.get("image"),
                    "video": raw_banner.get("video"),
                }
            elif raw_banner is not None:
                banner = {"image": str(raw_banner), "video": None}

        enquiry_destination_name = None
        if enquiry is not None:
            destination_ref = getattr(enquiry, "destination_ref", None)
            enquiry_destination_name = getattr(destination_ref, "name", None)

        package_name = None
        if package is not None:
            package_name = getattr(package, "title", None) or getattr(package, "name", None)

        variant_name = getattr(variant, "name", None) if variant is not None else None
        if variant is not None and variant_name is None:
            variant_name = getattr(variant, "title", None)

        return {
            "id": value.id,
            "booking_code": value.booking_code,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": getattr(customer, "email", None),
                "mobile": getattr(customer, "mobile", None),
                "profile_pic": getattr(customer, "profile_pic", None),
            } if customer else None,
            "enquiry": {
                "id": enquiry.id,
                "destination_id": getattr(enquiry, "destination_id", None),
                "destination_name": enquiry_destination_name,
            } if enquiry else None,
            "package": {
                "id": package.id,
                "name": package_name,
                "season": getattr(variant, "season_name", None) if variant is not None else None,
            } if package or variant else None,
            "variant": {
                "id": variant.id,
                "name": variant_name,
                "banner": banner,
            } if variant else None,
            "departure": {
                "id": departure.id,
                "departure_date": getattr(departure, "departure_date", None),
                "return_date": getattr(departure, "return_date", None),
            } if departure else None,
            "booking_type": getattr(value, "booking_type", None),
            "source": getattr(value, "source", None),
            "status": getattr(value, "status", None),
            "total_amount": getattr(value, "total_amount", None),
            "paid_amount": getattr(value, "paid_amount", None),
            "due_amount": getattr(value, "due_amount", None),
        }


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
    quotation_id: UUID | None = None
    offer: BookingOfferSummaryResponse | None = None
    sales_account: BookingAccountSummaryResponse | None = None
    adult_count: int | None = None
    child_count: int | None = None
    senior_count: int | None = None
    subtotal: Decimal | None = None
    discount_amount: Decimal | None = None
    notes: str | None = None
    created_by: BookingAccountSummaryResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    travellers: list[BookingTravelerResponse] = Field(default_factory=list)
    items: list[BookingTripItemResponse] = Field(default_factory=list)
    itinerary: list[QuotationItineraryResponse] = Field(default_factory=list)
    status_history: list[BookingStatusHistoryResponse] = Field(default_factory=list)
    customer_name: str | None = None
    customer_mobile: str | None = None
    gross_profit: Decimal | None = None
    profit_margin: float | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_booking_detail_response(cls, value):
        if isinstance(value, dict):
            return value

        if value is None:
            return None

        base = BookingResponse.normalize_booking_response(value)
        if isinstance(base, dict):
            offer = getattr(value, "offer", None)
            sales_account = getattr(value, "sales_account", None)
            created_by_account = getattr(value, "created_by_account", None)
            customer = getattr(value, "customer", None)

            base.update({
                "quotation_id": getattr(value, "quotation_id", None),
                "offer": {"id": offer.id, "name": getattr(offer, "name", None)} if offer else None,
                "sales_account": {
                    "id": sales_account.id,
                    "name": sales_account.name,
                    "email": getattr(sales_account, "email", None),
                    "mobile": getattr(sales_account, "mobile", None),
                    "profile_pic": getattr(sales_account, "profile_pic", None),
                } if sales_account else None,
                "adult_count": getattr(value, "adult_count", None),
                "child_count": getattr(value, "child_count", None),
                "senior_count": getattr(value, "senior_count", None),
                "subtotal": getattr(value, "subtotal", None),
                "discount_amount": getattr(value, "discount_amount", None),
                "notes": getattr(value, "notes", None),
                "created_by": {
                    "id": created_by_account.id,
                    "name": created_by_account.name,
                    "email": getattr(created_by_account, "email", None),
                    "mobile": getattr(created_by_account, "mobile", None),
                    "profile_pic": getattr(created_by_account, "profile_pic", None),
                } if created_by_account else None,
                "created_at": getattr(value, "created_at", None),
                "updated_at": getattr(value, "updated_at", None),
                "travellers": [trav.model_dump(exclude_none=True) for trav in getattr(value, "travellers", []) or []],
                "items": [item.model_dump(exclude_none=True) for item in getattr(value, "trip_items", []) or []],
                "itinerary": [day.model_dump(exclude_none=True) for day in getattr(value, "trip_itinerary", []) or []],
                "status_history": [history.model_dump(exclude_none=True) for history in getattr(value, "status_history", []) or []],
                "customer_name": getattr(customer, "name", None) if customer else None,
                "customer_mobile": getattr(customer, "mobile", None) if customer else None,
            })
            return base
        return value
