# app/models/custom_tour_request.py

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CustomTourRequest(Base):
    __tablename__ = "custom_tour_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    visitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mobile: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    travel_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    adults: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    children: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    budget: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    requirements: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="NEW",
        nullable=False,
        index=True,
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