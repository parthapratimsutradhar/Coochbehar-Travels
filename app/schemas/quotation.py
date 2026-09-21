from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.core.enums import CostItemType, QuotationStatus
from app.schemas.base import SchemaBase


class QuotationItemBase(SchemaBase):
    item_type: CostItemType = CostItemType.OTHER
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal(0), ge=0)
    total_price: Decimal = Field(default=Decimal(0), ge=0)


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
    offer_id: UUID | None = None
    destination_id: UUID | None = None
    hotel_id: UUID | None = None
    room_id: UUID | None = None
    vehicle_id: UUID | None = None
    tour_name: str = Field(..., min_length=1, max_length=255)
    travel_date: datetime | None = None
    return_date: datetime | None = None
    adult_count: int = Field(default=1, ge=0)
    child_count: int = Field(default=0, ge=0)
    senior_count: int = Field(default=0, ge=0)
    room_count: int = Field(default=1, ge=1)
    vehicle_count: int | None = Field(default=None, ge=1)
    meal_plan: str | None = Field(default=None, max_length=255)
    subtotal: Decimal = Field(default=Decimal(0), ge=0)
    discount_amount: Decimal = Field(default=Decimal(0), ge=0)
    tax_amount: Decimal = Field(default=Decimal(0), ge=0)
    total_amount: Decimal = Field(default=Decimal(0), ge=0)
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None


class QuotationCreate(QuotationBase):
    items: list[QuotationItemCreate] = []


class QuotationUpdate(SchemaBase):
    destination_id: UUID | None = None
    hotel_id: UUID | None = None
    room_id: UUID | None = None
    vehicle_id: UUID | None = None
    tour_name: str | None = Field(default=None, min_length=1, max_length=255)
    travel_date: datetime | None = None
    return_date: datetime | None = None
    adult_count: int | None = Field(default=None, ge=0)
    child_count: int | None = Field(default=None, ge=0)
    senior_count: int | None = Field(default=None, ge=0)
    room_count: int | None = Field(default=None, ge=1)
    vehicle_count: int | None = Field(default=None, ge=1)
    meal_plan: str | None = Field(default=None, max_length=255)
    subtotal: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    total_amount: Decimal | None = Field(default=None, ge=0)
    offer_id: UUID | None = None
    valid_until: datetime | None = None
    terms_and_conditions: str | None = None
    rejected_reason: str | None = None
    status: QuotationStatus | None = None
    items: list[QuotationItemCreate] | None = None


class QuotationStatusUpdate(SchemaBase):
    status: QuotationStatus


class QuotationResponse(QuotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quotation_code: str
    version: int
    status: QuotationStatus
    created_by_account_id: UUID | None
    sent_at: datetime | None
    accepted_at: datetime | None
    rejected_at: datetime | None
    rejected_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemResponse] = []


class QuotationConvertToBookingRequest(SchemaBase):
    booking_type: str = "PACKAGE"
    notes: str | None = None
