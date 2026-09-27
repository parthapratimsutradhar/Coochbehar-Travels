"""Visitor, session, event schemas — enduser tracking + admin analytics."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase


# ── Base & Legacy Schemas (Preserved for backwards compatibility) ──────

class VisitorBase(SchemaBase):
    fingerprint: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    browser: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    device: str | None = Field(default=None, max_length=100)
    customer_id: UUID | None = None


class VisitorCreate(VisitorBase):
    pass


class VisitorResponse(VisitorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visitor_code: str
    first_seen: datetime
    last_seen: datetime


class VisitorSessionBase(SchemaBase):
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
    page_views: int
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None


class VisitorEventBase(SchemaBase):
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
    created_at: datetime


# ── Enduser Tracking Request Schemas ──────────────────────────────────

class VisitorIdentifyRequest(SchemaBase):
    fingerprint: str | None = Field(default=None, max_length=255, description="Client browser fingerprint")
    ip_address: str | None = Field(default=None, max_length=45)
    country: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    browser: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    device: str | None = Field(default=None, max_length=100)
    customer_id: UUID | None = None


class VisitorIdentifyResponse(SchemaBase):
    visitor: VisitorResponse
    is_new: bool = Field(description="True if visitor record was newly created")


class SessionStartRequest(SchemaBase):
    visitor_id: UUID
    landing_page: str | None = Field(default=None, description="URL of entry page")
    referrer: str | None = Field(default=None, description="HTTP Referrer URL")
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)
    utm_term: str | None = Field(default=None, max_length=100)
    utm_content: str | None = Field(default=None, max_length=100, description="Stored in event metadata")


class SessionHeartbeatRequest(SchemaBase):
    current_page: str | None = Field(default=None, description="Current page URL")
    page_views_delta: int = Field(default=0, ge=0, description="Additional page views since last heartbeat")


class SessionEndRequest(SchemaBase):
    exit_page: str | None = Field(default=None, description="URL of exit page")


class EventTrackRequest(SchemaBase):
    visitor_id: UUID
    session_id: UUID
    event_name: str = Field(..., max_length=100, description="e.g. tour_package_view, enquiry_submit, scroll_depth_50")
    page: str | None = Field(default=None, description="Page URL where event occurred")
    event_metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary event payload JSON")


class EventBatchRequest(SchemaBase):
    events: list[EventTrackRequest] = Field(..., min_length=1, max_length=50, description="Batch of up to 50 events")


class EventBatchResponse(SchemaBase):
    accepted_count: int
    events: list[VisitorEventResponse]


class VisitorProfileResponse(SchemaBase):
    visitor: VisitorResponse
    sessions: list[VisitorSessionResponse]
    recent_events: list[VisitorEventResponse]
    total_events: int
    total_sessions: int


# ── Live Presence Schemas ─────────────────────────────────────────────

class LiveVisitorItem(SchemaBase):
    """A single live visitor as seen in the admin presence panel."""
    visitor_id: str
    session_id: str | None = None
    customer_id: str | None = None
    visitor_type: str = Field(default="visitor", description="'customer' or 'visitor'")
    visitor_code: str | None = None
    customer_name: str | None = None
    is_anonymous: bool = True
    page: str | None = None
    activity: str | None = None
    source: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    referrer: str | None = None
    current_url: str | None = None
    device: str | None = None
    browser: str | None = None
    os: str | None = None
    ip_address: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    session_start: str | None = None
    last_activity: str | None = None
    connected_at: str | None = None


class LiveStatsResponse(SchemaBase):
    total: int = Field(description="Total active connections")
    customers: int = Field(description="Active logged-in customers")
    visitors: int = Field(description="Active anonymous visitors")
    active_visitors: list[LiveVisitorItem] = Field(default_factory=list)
    timestamp: str


# ── Admin Analytics Response Schemas ──────────────────────────────────

DateFilter = Literal["today", "yesterday", "7d", "30d", "90d"]


class AnalyticsStatsResponse(SchemaBase):
    """Date-filtered statistical overview for admin analytics dashboard."""
    total_visitors: int
    total_customers: int
    total_anonymous_visitors: int
    total_events: int
    total_page_views: int
    total_sessions: int
    avg_session_duration_seconds: float
    avg_page_views_per_session: float
    date_filter: str
    period_start: str
    period_end: str


class AnalyticsOverviewResponse(SchemaBase):
    total_visitors: int
    visitors_today: int
    active_sessions: int
    total_events_today: int
    average_lead_score: float
    high_intent_visitors_count: int


class TopPageItem(SchemaBase):
    page: str
    views: int
    unique_visitors: int
    rank: int = 1


class TopEventItem(SchemaBase):
    event_name: str
    count: int
    category: str | None = None


class TrafficSourceItem(SchemaBase):
    source: str = Field(description="direct | organic | social | referral | paid | email | utm_campaign")
    sessions: int
    visitors: int
    percentage: float


class LocationRankItem(SchemaBase):
    location: str = Field(description="Country or City name")
    location_type: str = Field(description="'country' or 'city'")
    visitors: int
    customers: int
    total: int
    percentage: float
    rank: int


class UtmPerformanceItem(SchemaBase):
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    session_count: int
    conversion_count: int
    avg_duration_seconds: float


class FunnelStageItem(SchemaBase):
    stage: str
    visitor_count: int
    conversion_rate: float


class LeadScoreDistributionItem(SchemaBase):
    score_range: str
    count: int
