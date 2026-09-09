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
    payment_terms: str | None = Field(default=None, max_length=100)
    status: str = Field(default="ACTIVE", max_length=30)


class VendorCreate(VendorBase):
    vendor_code: str | None = None


class VendorUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    contact: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    payment_terms: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=30)


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_code: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
