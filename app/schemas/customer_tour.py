from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.schemas.booking import BookingDetailResponse
from app.schemas.base import SchemaBase


class CustomerTourResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tour_name: str
    destination: str | None = None
    travel_date: date | None = None
    return_date: date | None = None
    pax_no: int | None = None
    total_amount: Decimal | None = None
    status: str
    notes: str | None = None
    package_id: UUID | None = None
    variant_id: UUID | None = None
    enquiry_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class CustomerTourDetailResponse(BookingDetailResponse):
    gross_profit: Decimal | None = Field(default=None, exclude=True)
    profit_margin: float | None = Field(default=None, exclude=True)