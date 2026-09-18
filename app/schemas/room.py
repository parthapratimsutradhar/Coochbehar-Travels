from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.enums import RoomType
from app.schemas.base import SchemaBase
from app.schemas.hotel import GalleryItem


class RoomBase(SchemaBase):
    room_number: str = Field(..., min_length=1, max_length=20)
    room_image: list[GalleryItem] = Field(..., min_length=1)
    room_type: RoomType
    capacity: int = Field(..., gt=0)
    price_per_night: Decimal = Field(..., ge=0, decimal_places=2)
    description: str | None = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(SchemaBase):
    room_number: str | None = Field(default=None, min_length=1, max_length=20)
    room_image: list[GalleryItem] | None = Field(default=None, min_length=1)
    room_type: RoomType | None = None
    capacity: int | None = Field(default=None, gt=0)
    price_per_night: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    description: str | None = None
    is_active: bool | None = None


class RoomResponse(RoomBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    room_image: list[GalleryItem] = Field(default_factory=list)
    id: UUID
    hotel_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime