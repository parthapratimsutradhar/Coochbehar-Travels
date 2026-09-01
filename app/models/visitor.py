import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity


class Visitor(UUIDEntity):
    __tablename__ = "visitors"

    visitor_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    fingerprint: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    os: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    device: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

# ── Relationships ───────────────────────────────────────────────────────
    customer = relationship("Customer", back_populates="visitors")
    sessions = relationship("VisitorSession", back_populates="visitor", cascade="all, delete-orphan")
    events = relationship("VisitorEvent", back_populates="visitor", cascade="all, delete-orphan")
    enquiries = relationship("Enquiry", back_populates="visitor")
    leads = relationship("Lead", back_populates="visitor")