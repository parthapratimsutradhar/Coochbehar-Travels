import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.otp_challenge import OtpChallenge


class OtpRepository:
    """Repository for OTP challenges and identity verification operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_challenge(
        self,
        identifier: str,
        identifier_type: str,
        otp_hash: str,
        purpose: str = "LOGIN",
        expires_in_seconds: int | None = None,
        visitor_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> OtpChallenge:
        """Create a new unverified OTP challenge."""
        if expires_in_seconds is None:
            expires_in_seconds = settings.OTP_EXPIRY_SECONDS

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in_seconds)

        challenge = OtpChallenge(
            identifier=identifier.strip(),
            identifier_type=identifier_type.upper(),
            otp_hash=otp_hash,
            purpose=purpose,
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            is_used=False,
            expires_at=expires_at,
            created_at=now,
            visitor_id=visitor_id,
            customer_id=customer_id,
        )
        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)
        return challenge

    def get_active_challenge(
        self,
        identifier: str,
        purpose: str = "LOGIN",
    ) -> OtpChallenge | None:
        """Retrieve the latest active (unused, unexpired) OTP challenge for an identifier."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(OtpChallenge)
            .where(
                OtpChallenge.identifier == identifier.strip(),
                OtpChallenge.purpose == purpose,
                OtpChallenge.is_used == False,  # noqa: E712
                OtpChallenge.expires_at > now,
            )
            .order_by(OtpChallenge.created_at.desc())
        )
        return self.db.execute(stmt).scalars().first()

    def increment_attempts(self, challenge: OtpChallenge) -> int:
        """Increment failed attempts counter and return new count."""
        challenge.attempts += 1
        self.db.commit()
        self.db.refresh(challenge)
        return challenge.attempts

    def mark_used(
        self,
        challenge: OtpChallenge,
        customer_id: uuid.UUID | None = None,
    ) -> None:
        """Mark challenge as successfully verified and consumed."""
        challenge.is_used = True
        challenge.verified_at = datetime.now(timezone.utc)
        if customer_id and not challenge.customer_id:
            challenge.customer_id = customer_id
        self.db.commit()
        self.db.refresh(challenge)

    def invalidate_existing(
        self,
        identifier: str,
        purpose: str = "LOGIN",
    ) -> None:
        """Invalidate previous unverified challenges for an identifier."""
        stmt = (
            update(OtpChallenge)
            .where(
                OtpChallenge.identifier == identifier.strip(),
                OtpChallenge.purpose == purpose,
                OtpChallenge.is_used == False,  # noqa: E712
            )
            .values(is_used=True)
        )
        self.db.execute(stmt)
        self.db.commit()
