from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import LeadSource


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_mobile: str | None = Field(default=None, max_length=20)
    profile_pic: str | None = Field(default=None, max_length=500, description="Customer avatar image URL")
    source: LeadSource = LeadSource.WEBSITE
    is_imported: bool = False


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_mobile: str | None = Field(default=None, max_length=20)
    profile_pic: str | None = Field(default=None, max_length=500)
    source: LeadSource | None = None
    is_imported: bool | None = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_code: str
    created_at: datetime
    updated_at: datetime
