import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.core.enums import OfferDiscountType, OfferStatus
from app.schemas.base import SchemaBase


class TourOfferApplyRequest(SchemaBase):
    offer_id: uuid.UUID


class TourOfferVariantsUpdate(SchemaBase):
    variant_ids: list[uuid.UUID] = Field(default_factory=list)


class TourOfferVariantResponse(SchemaBase):
    id: uuid.UUID
    package_id: uuid.UUID
    slug: str
    name: str
    season_name: str | None = None
    valid_from: date
    valid_to: date
    duration_days: int
    duration_nights: int
    list_price: Decimal
    selling_price: Decimal
    badge: str | None = None
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class TourOfferCreate(SchemaBase):
    name: str
    description: str | None = None
    discount_type: OfferDiscountType
    discount_value: Decimal = Field(..., ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    min_booking_amount: Decimal | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    per_customer_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime
    valid_until: datetime
    status: OfferStatus = OfferStatus.DRAFT


class TourOfferUpdate(SchemaBase):
    name: str | None = None
    description: str | None = None
    discount_type: OfferDiscountType | None = None
    discount_value: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    min_booking_amount: Decimal | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    per_customer_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: OfferStatus | None = None


class TourOfferBaseResponse(SchemaBase):
    id: uuid.UUID
    name: str
    description: str | None = None
    status: OfferStatus
    discount_type: OfferDiscountType
    discount_value: Decimal
    max_discount_amount: Decimal | None = None
    min_booking_amount: Decimal | None = None
    usage_limit: int | None = None
    usage_count: int = 0
    per_customer_limit: int | None = None
    valid_from: datetime
    valid_until: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TourOfferListResponse(TourOfferBaseResponse):
    pass


class TourOfferCalculationResult(SchemaBase):
    offer_id: uuid.UUID | None = None
    original_amount: Decimal
    discount_type: OfferDiscountType
    discount_value: Decimal
    calculated_discount: Decimal
    applied_discount: Decimal
    final_amount: Decimal
