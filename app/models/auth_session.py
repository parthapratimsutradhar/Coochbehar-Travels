import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity
from app.core.enums import ActorType


class AuthSession(UUIDEntity):
    """Server-side authentication refresh session model.

    Supports both internal staff/admin (User) and enduser/travelers (Customer).
    Tracks issued opaque refresh tokens by their cryptographic hash,
    enforcing absolute 30-day expiration and sliding inactivity timeout,
    and automatic token rotation / replay detection.
    """

    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type"),
        nullable=False,
        default=ActorType.USER,
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

# ── Relationships ───────────────────────────────────────────────────────
    user = relationship("User", back_populates="auth_sessions")
    customer = relationship("Customer", back_populates="auth_sessions")
