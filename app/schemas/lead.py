from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import EnquiryChannel, LeadSource, LeadStatus


class LeadActivityBase(BaseModel):
    channel: EnquiryChannel
    activity_type: str = Field(..., max_length=50)
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class LeadActivityCreate(LeadActivityBase):
    lead_id: UUID
    user_id: UUID | None = None


class LeadActivityResponse(LeadActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    user_id: UUID | None
    created_at: datetime


class LeadBase(BaseModel):
    full_name: str = Field(..., max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool = False
    lead_score: int = 0
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.WEBSITE
    notes: str | None = None


class LeadCreate(LeadBase):
    enquiry_id: UUID | None = None
    customer_id: UUID | None = None
    visitor_id: UUID | None = None


class LeadUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    whatsapp_opt_in: bool | None = None
    lead_score: int | None = None
    status: LeadStatus | None = None
    source: LeadSource | None = None
    notes: str | None = None
    last_contacted_at: datetime | None = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_code: str
    enquiry_id: UUID | None
    customer_id: UUID | None
    visitor_id: UUID | None
    last_contacted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    activities: list[LeadActivityResponse] = []
