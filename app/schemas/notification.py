from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, ConfigDict
from app.schemas.base import SchemaBase


class NotificationResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    title: str
    message: str
    image_url: str | None = None
    action_url: str | None = None
    data: dict[str, Any] | None = None
    is_read: bool
    read_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class NotificationCreate(SchemaBase):
    notification_type: str = Field(default="GENERAL", max_length=50)
    title: str = Field(..., min_length=1, max_length=160)
    message: str = Field(..., min_length=1, max_length=5000)
    image_url: str | None = Field(default=None, max_length=1000)
    action_url: str | None = Field(default=None, max_length=1000)
    data: dict[str, Any] | None = None
    expires_at: datetime | None = None


class AdminNotificationCreate(NotificationCreate):
    customer_ids: list[UUID] | None = Field(default=None, max_length=1000)
    user_ids: list[UUID] | None = Field(default=None, max_length=1000)
    broadcast_customers: bool = False
    broadcast_staff: bool = False


class NotificationListResponse(SchemaBase):
    items: list[NotificationResponse]
    unread_count: int
