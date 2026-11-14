from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import HotelCategory
from app.schemas.base import SchemaBase


class HotelBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=255)
    destination_id: UUID | None = None
    category: HotelCategory | None = None
    address: str | None = Field(default=None, max_length=255)
    description: str | None = None


class HotelCreate(HotelBase):
    pass


class HotelUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    destination_id: UUID | None = None
    category: HotelCategory | None = None
    address: str | None = Field(default=None, max_length=255)
    description: str | None = None


class HotelResponse(HotelBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
