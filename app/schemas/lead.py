from datetime import datetime
from uuid import UUID

from pydantic import Field, ConfigDict, AliasChoices
from app.schemas.base import SchemaBase

from app.core.enums import (
    LeadChannel,
    LeadActivityType,
    LeadLostReason,
    LeadStatus,
)


class LeadActivityBase(SchemaBase):
    channel: LeadChannel
    activity_type: LeadActivityType
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class LeadActivityCreate(LeadActivityBase):
    lead_id: UUID
    account_id: UUID | None = Field(default=None, validation_alias=AliasChoices("account_id", "user_id"))
    user_id: UUID | None = None


class AdminLeadActivityCreate(LeadActivityBase):
    account_id: UUID | None = Field(default=None, validation_alias=AliasChoices("account_id", "user_id"))
    user_id: UUID | None = None


class LeadActivityUpdate(SchemaBase):
    channel: LeadChannel | None = None
    activity_type: LeadActivityType | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class LeadAssignmentUpdate(SchemaBase):
    assigned_account_id: UUID | None


class LeadStatusUpdate(SchemaBase):
    status: LeadStatus
    lost_reason: LeadLostReason | None = None
    lost_reason_notes: str | None = Field(default=None, max_length=1000)


class LeadManageUpdate(SchemaBase):
    assigned_account_id: UUID | None = None
    status: LeadStatus | None = None
    qualification_notes: str | None = Field(default=None, max_length=1000)
    lost_reason: LeadLostReason | None = None
    lost_reason_notes: str | None = Field(default=None, max_length=1000)


class LeadActivityResponse(LeadActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    user_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("user_id", "account_id"),
        serialization_alias="user_id",
    )
    created_at: datetime
    updated_at: datetime


class LeadBase(SchemaBase):
    lead_score: int = 0
    status: LeadStatus = LeadStatus.NEW


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_code: str
    enquiry_id: UUID | None
    assigned_account_id: UUID | None
    last_contacted_at: datetime | None
    qualified_at: datetime | None
    converted_at: datetime | None
    lost_at: datetime | None
    lost_reason: LeadLostReason | None
    lost_reason_notes: str | None
    qualification_notes: str | None
    created_at: datetime
    updated_at: datetime
    activities: list[LeadActivityResponse] = []


class LeadSummaryResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_score: int
    status: LeadStatus
    assigned_account_id: UUID | None
    last_contacted_at: datetime | None
    qualified_at: datetime | None
    converted_at: datetime | None
    lost_at: datetime | None
    lost_reason: LeadLostReason | None


