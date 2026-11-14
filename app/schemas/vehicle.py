from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import VehicleType
from app.schemas.base import SchemaBase


class VehicleBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=100)
    vehicle_type: VehicleType = VehicleType.ANY
    registration_number: str | None = Field(default=None, max_length=50)
    capacity: int = Field(default=1, ge=1)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    vehicle_type: VehicleType | None = None
    registration_number: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class VehicleResponse(VehicleBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
