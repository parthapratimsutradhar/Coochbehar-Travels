import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lead_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
    )

    mobile: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
    )

    whatsapp_opt_in: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    lead_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="NEW",
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    visitors = relationship(
        "Visitor",
        back_populates="lead",
    )