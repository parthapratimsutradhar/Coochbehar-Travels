from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VisitorBase(BaseModel):
    fingerprint: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    browser: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    device: str | None = Field(default=None, max_length=100)
    customer_id: UUID | None = None
    lead_score: int = 0


class VisitorCreate(VisitorBase):
    pass


class VisitorResponse(VisitorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_code: str
    first_seen: datetime
    last_seen: datetime


class VisitorSessionBase(BaseModel):
    visitor_id: UUID
    landing_page: str | None = None
    exit_page: str | None = None
    referrer: str | None = None
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)
    utm_term: str | None = Field(default=None, max_length=100)


class VisitorSessionCreate(VisitorSessionBase):
    pass


class VisitorSessionResponse(VisitorSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_code: str
    page_views: int
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None


class VisitorEventBase(BaseModel):
    visitor_id: UUID
    session_id: UUID
    event_name: str = Field(..., max_length=100)
    page: str | None = None
    event_metadata: dict[str, Any] | None = None


class VisitorEventCreate(VisitorEventBase):
    pass


class VisitorEventResponse(VisitorEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_code: str
    created_at: datetime
