from datetime import datetime
from uuid import UUID
from pydantic import ConfigDict, Field
from app.schemas.base import SchemaBase


class VendorBase(SchemaBase):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=50, description="e.g. HOTEL, TRANSPORT, DMC, GUIDE")
    contact: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    contact: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
