from datetime import datetime
from uuid import UUID
from pydantic import ConfigDict, Field
from app.schemas.base import SchemaBase


class DestinationBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=1000)
    is_domestic: bool = True
    is_featured: bool = False
    is_popular: bool = False


class DestinationCreate(DestinationBase):
    pass


class DestinationUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=1000)
    is_domestic: bool | None = None
    is_featured: bool | None = None
    is_popular: bool | None = None
    is_active: bool | None = None


class DestinationResponse(DestinationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
