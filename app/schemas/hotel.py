from datetime import datetime
import uuid
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import HotelCategory
from app.schemas.base import SchemaBase


class GalleryItem(SchemaBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alt: str | None = None
    url: str
    type: str | None = None
    display_order: int | None = None

    model_config = ConfigDict(extra="allow")


class HotelBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=255)
    image: list[GalleryItem] = Field(..., min_length=1)
    destination_id: UUID | None = None
    category: HotelCategory | None = None
    address: str | None = Field(default=None, max_length=255)
    contact: str | None = Field(default=None, max_length=100)
    description: str | None = None


class HotelCreate(HotelBase):
    pass


class HotelUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    image: list[GalleryItem] | None = Field(default=None, min_length=1)
    destination_id: UUID | None = None
    category: HotelCategory | None = None
    address: str | None = Field(default=None, max_length=255)
    contact: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class HotelResponse(HotelBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
