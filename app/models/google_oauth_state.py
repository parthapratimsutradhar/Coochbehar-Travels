import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity


class GoogleOAuthState(UUIDEntity):
    """Server-side CSRF state for Google OAuth flow.

    Short-lived entries (5 min TTL) used to verify the OAuth callback
    state parameter. Supports admin login, customer login, and
    Google account linking flows for both web and Android.
    """

    __tablename__ = "google_oauth_states"

    state_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Random CSRF state token",
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="ADMIN_LOGIN, CUSTOMER_LOGIN, CUSTOMER_LINK",
    )

    redirect_uri: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Where to redirect after auth",
    )

    visitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    visitor = relationship("Visitor")
