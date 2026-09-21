import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class Notification(BaseEntity):
    __tablename__ = "notifications"

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    action_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    recipient_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        JSON().with_variant(ARRAY(UUID(as_uuid=True)), "postgresql"),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    campaigns = relationship(
        "NotificationCampaign",
        back_populates="notification",
        cascade="all, delete-orphan",
    )