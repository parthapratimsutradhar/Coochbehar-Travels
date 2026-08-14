import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    visitor_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    fingerprint: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
    )

    os: Mapped[str | None] = mapped_column(
        String(100),
    )

    device: Mapped[str | None] = mapped_column(
        String(100),
    )

    lead_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    lead = relationship(
        "Lead",
        back_populates="visitors",
    )

    sessions = relationship(
        "VisitorSession",
        back_populates="visitor",
        cascade="all, delete-orphan",
    )