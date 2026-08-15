import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity


class VisitorEvent(UUIDEntity):
    __tablename__ = "visitor_events"

    event_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    visitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"),
        index=True,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visitor_sessions.id", ondelete="CASCADE"),
        index=True,
    )

    event_name: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    page: Mapped[str | None] = mapped_column(
        Text,
    )

    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    visitor = relationship(
        "Visitor",
        back_populates="events",
    )

    session = relationship(
        "VisitorSession",
        back_populates="events",
    )