import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDEntity


class OtpChallenge(UUIDEntity):
    """Persisted OTP challenge for identity verification.

    Stores bcrypt-hashed OTP — NEVER plaintext.
    Supports both admin (User) and end-user (Customer/Visitor) verification flows.
    """

    __tablename__ = "otp_challenges"

    identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Mobile number or email being verified",
    )

    identifier_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="MOBILE or EMAIL",
    )

    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt-hashed OTP, never plaintext",
    )

    purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="LOGIN, VERIFY_MOBILE, VERIFY_EMAIL",
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    visitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visitors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    visitor = relationship("Visitor")
    customer = relationship("Customer")
