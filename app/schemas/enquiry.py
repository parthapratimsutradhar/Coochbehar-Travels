from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EnquiryChannel, EnquiryStatus, EnquiryType


class EnquiryBase(BaseModel):
    enquiry_type: EnquiryType
    channel: EnquiryChannel
    package_id: UUID | None = None
    variant_id: UUID | None = None
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = None


class EnquiryCreate(EnquiryBase):
    visitor_id: UUID | None = None
    customer_id: UUID | None = None


class EnquiryUpdate(BaseModel):
    status: EnquiryStatus | None = None
    subject: str | None = Field(default=None, max_length=200)
    message: str | None = None


class EnquiryResponse(EnquiryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enquiry_code: str
    visitor_id: UUID | None
    customer_id: UUID | None
    status: EnquiryStatus
    created_at: datetime
    updated_at: datetime
