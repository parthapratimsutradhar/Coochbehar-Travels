import uuid
from datetime import datetime, timezone
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession
from app.utils.security import normalize_role_value


class AuthSessionRepository:
    """Repository for server-side auth sessions and refresh token management."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(
        self,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        actor_type: str = "ADMIN",
        refresh_token_hash: str = "",
        expires_at: datetime | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthSession:
        """Create a new server-side authentication session."""
        now = datetime.now(timezone.utc)
        normalized_actor_type = normalize_role_value(actor_type, default="ADMIN")
        session = AuthSession(
            user_id=user_id,
            customer_id=customer_id,
            actor_type=normalized_actor_type,
            refresh_token_hash=refresh_token_hash,
            created_at=now,
            last_used_at=now,
            expires_at=expires_at,
            revoked_at=None,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        """Find an auth session by the SHA-256 hash of its refresh token."""
        stmt = select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, session_id: uuid.UUID) -> AuthSession | None:
        """Find an auth session by ID."""
        stmt = select(AuthSession).where(AuthSession.id == session_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_sessions_for_actor(
        self,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> list[AuthSession]:
        """Fetch all currently non-revoked, unexpired sessions for a user or customer."""
        now = datetime.now(timezone.utc)
        stmt = select(AuthSession).where(
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        if user_id:
            stmt = stmt.where(AuthSession.user_id == user_id)
        elif customer_id:
            stmt = stmt.where(AuthSession.customer_id == customer_id)
        else:
            return []

        stmt = stmt.order_by(AuthSession.last_used_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def revoke_session(self, session: AuthSession) -> None:
        """Mark a single session as revoked."""
        if session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(session)

    def revoke_all_for_actor(
        self,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        exclude_session_id: uuid.UUID | None = None,
    ) -> int:
        """Revoke active sessions, optionally preserving one session."""
        now = datetime.now(timezone.utc)
        stmt = update(AuthSession).where(AuthSession.revoked_at.is_(None)).values(revoked_at=now)
        if user_id:
            stmt = stmt.where(AuthSession.user_id == user_id)
        elif customer_id:
            stmt = stmt.where(AuthSession.customer_id == customer_id)
        else:
            return 0
        if exclude_session_id:
            stmt = stmt.where(AuthSession.id != exclude_session_id)

        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount

    def rotate_session(
        self,
        old_session: AuthSession,
        new_token_hash: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthSession:
        """Rotate a refresh token:

        1. Invalidate/revoke the old session.
        2. Create a new session inheriting the original absolute `expires_at`.
        3. Update `last_used_at` to now.
        """
        now = datetime.now(timezone.utc)

        # Invalidate old session
        old_session.revoked_at = now

        # Create new rotated session keeping original absolute expiration
        new_session = AuthSession(
            user_id=old_session.user_id,
            customer_id=old_session.customer_id,
            actor_type=old_session.actor_type,
            refresh_token_hash=new_token_hash,
            created_at=old_session.created_at,  # preserve original login timestamp
            last_used_at=now,
            expires_at=old_session.expires_at,  # strictly retain original absolute 30-day deadline
            revoked_at=None,
            user_agent=user_agent or old_session.user_agent,
            ip_address=ip_address or old_session.ip_address,
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session
