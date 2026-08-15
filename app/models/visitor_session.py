import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDEntity


class VisitorSession(UUIDEntity):
    __tablename__ = "visitor_sessions"

    session_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    visitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"),
        index=True,
    )

    landing_page: Mapped[str | None] = mapped_column(
        Text,
    )

    exit_page: Mapped[str | None] = mapped_column(
        Text,
    )

    referrer: Mapped[str | None] = mapped_column(
        Text,
    )

    utm_source: Mapped[str | None] = mapped_column(
        String(100),
    )

    utm_medium: Mapped[str | None] = mapped_column(
        String(100),
    )

    utm_campaign: Mapped[str | None] = mapped_column(
        String(100),
    )

    utm_term: Mapped[str | None] = mapped_column(
        String(100),
    )

    page_views: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    visitor = relationship(
        "Visitor",
        back_populates="sessions",
    )

    events = relationship(
        "VisitorEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )