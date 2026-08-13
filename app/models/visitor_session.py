# app/models/visitor_session.py

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VisitorSession(Base):
    __tablename__ = "visitor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    visitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    landing_page: Mapped[str | None] = mapped_column(Text)

    exit_page: Mapped[str | None] = mapped_column(Text)

    page_views: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    referrer: Mapped[str | None] = mapped_column(Text)

    utm_source: Mapped[str | None] = mapped_column(String(100))

    utm_medium: Mapped[str | None] = mapped_column(String(100))

    utm_campaign: Mapped[str | None] = mapped_column(String(100))

    utm_term: Mapped[str | None] = mapped_column(String(100))

    visitor = relationship("Visitor")