from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import VehicleType
from app.schemas.base import SchemaBase
from app.schemas.hotel import GalleryItem


class VehicleBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=100)
    vehicle_image: list[GalleryItem] = Field(..., min_length=1)
    vehicle_type: VehicleType = VehicleType.ANY
    registration_number: str | None = Field(default=None, max_length=50)
    capacity: int = Field(default=1, ge=1)
    price_per_day: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    vehicle_image: list[GalleryItem] | None = Field(default=None, min_length=1)
    vehicle_type: VehicleType | None = None
    registration_number: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, ge=1)
    price_per_day: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    is_active: bool | None = None


class VehicleResponse(VehicleBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    vehicle_image: list[GalleryItem] = Field(default_factory=list)
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VehiclePublicResponse(VehicleBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    vehicle_image: list[GalleryItem] = Field(default_factory=list)
    id: UUID
    created_at: datetime
    updated_at: datetime