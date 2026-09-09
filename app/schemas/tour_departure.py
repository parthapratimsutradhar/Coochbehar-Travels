from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import ConfigDict, Field
from app.schemas.base import SchemaBase


class TourDepartureBase(SchemaBase):
    variant_id: UUID
    departure_date: date
    return_date: date | None = None
    total_seats: int = Field(..., ge=0)
    available_seats: int = Field(..., ge=0)
    price: Decimal = Field(..., ge=0)


class TourDepartureCreate(TourDepartureBase):
    pass


class TourDepartureUpdate(SchemaBase):
    departure_date: date | None = None
    return_date: date | None = None
    total_seats: int | None = Field(default=None, ge=0)
    available_seats: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class TourDepartureResponse(TourDepartureBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
