import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import LeadSource, UserRole
from app.core.messages.validation import AuthError
from app.models.auth_session import AuthSession
from app.models.customer import Customer
from app.models.user import User
from app.repository.auth_session_repo import AuthSessionRepository
from app.repository.customer_repo import CustomerRepository
from app.repository.otp_repo import OtpRepository
from app.repository.user_repo import UserRepository
from app.schemas.auth import AuthSessionResponse
from app.services.email_service import EmailService
from app.utils.security import (
    create_access_token,
    generate_otp,
    generate_secure_token,
    hash_otp,
    hash_token,
    verify_google_id_token,
    verify_otp,
)


class AuthService:
    """Service layer coordinating pure OTP-based authentication, Google OAuth login,

    refresh token rotation, and multi-actor (Admin User vs Customer) sessions.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.otp_repo = OtpRepository(db)
        self.session_repo = AuthSessionRepository(db)
        self.email_service = EmailService()

    # ── Helper: Detect identifier type ─────────────────────────────────
    @staticmethod
    def detect_identifier_type(identifier: str) -> str:
        """Detect whether identifier is EMAIL or MOBILE."""
        if "@" in identifier:
            return "EMAIL"
        return "MOBILE"

    @classmethod
    def normalize_identifier(cls, identifier: str, identifier_type: str | None = None) -> tuple[str, str]:
        cleaned = identifier.strip()
        id_type = identifier_type.upper() if identifier_type else cls.detect_identifier_type(cleaned)
        if id_type == "EMAIL":
            cleaned = cleaned.lower()
        return cleaned, id_type

    def _dispatch_otp(self, identifier: str, identifier_type: str, raw_otp: str) -> str | None:
        if identifier_type == "EMAIL":
            self.email_service.send_otp_email(
                to_email=identifier,
                otp=raw_otp,
                expires_in_seconds=settings.OTP_EXPIRY_SECONDS,
            )
            return raw_otp if settings.IS_DEVELOPMENT else None

        if settings.IS_DEVELOPMENT:
            return raw_otp

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SMS OTP delivery is not configured. Use an email identifier for OTP login.",
        )

    # ── ADMIN OTP FLOWS ────────────────────────────────────────────────
    def request_admin_otp(
        self,
        identifier: str,
        purpose: str = "LOGIN",
    ) -> tuple[str, str, str, int, str | None]:
        """Generate and dispatch OTP for Admin / Staff user login."""
        cleaned, id_type = self.normalize_identifier(identifier)

        if id_type == "EMAIL":
            user = self.user_repo.get_by_email(cleaned)
        else:
            stmt = self.user_repo.get_by_mobile(cleaned) if hasattr(self.user_repo, "get_by_mobile") else None
            user = stmt or self.user_repo.get_by_email(cleaned)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin or staff user not found with this identifier.",
            )

        raw_otp = generate_otp(6)
        hashed = hash_otp(raw_otp)

        self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
        self.otp_repo.create_challenge(
            identifier=cleaned,
            identifier_type=id_type,
            otp_hash=hashed,
            purpose=purpose,
            expires_in_seconds=settings.OTP_EXPIRY_SECONDS,
        )

        try:
            returned_otp = self._dispatch_otp(cleaned, id_type, raw_otp)
        except HTTPException:
            self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
            raise

        message = f"OTP successfully generated and sent to your {id_type.lower()}."
        return message, cleaned, id_type, settings.OTP_EXPIRY_SECONDS, returned_otp

    def verify_admin_otp(
        self,
        identifier: str,
        otp: str,
        purpose: str = "LOGIN",
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """Verify Admin OTP, create server-side session, and return tokens."""
        cleaned, _ = self.normalize_identifier(identifier)
        challenge = self.otp_repo.get_active_challenge(cleaned, purpose=purpose)

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active OTP challenge found. Please request a new OTP.",
            )

        if challenge.attempts >= challenge.max_attempts:
            self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum verification attempts exceeded. Please request a new OTP.",
            )

        if not verify_otp(otp, challenge.otp_hash):
            attempts = self.otp_repo.increment_attempts(challenge)
            remaining = challenge.max_attempts - attempts
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
            )

        self.otp_repo.mark_used(challenge)

        if challenge.identifier_type == "EMAIL":
            user = self.user_repo.get_by_email(cleaned)
        else:
            user = self.user_repo.get_by_mobile(cleaned)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin user account is inactive or disabled.",
            )

        raw_refresh_token = generate_secure_token(64)
        refresh_token_hash = hash_token(raw_refresh_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = self.session_repo.create_session(
            user_id=user.id,
            customer_id=None,
            actor_type="ADMIN",
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.user_repo.update_last_login(user)

        access_token = create_access_token(
            subject=user.id,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            actor_type="ADMIN",
            email=user.email,
            mobile=user.mobile,
            extra_claims={"session_id": str(session.id)},
        )

        return access_token, raw_refresh_token, user

    # ── ADMIN GOOGLE OAUTH FLOW ────────────────────────────────────────
    def google_login_admin(
        self,
        id_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """Authenticate Admin user with Google OAuth ID token."""
        google_data = verify_google_id_token(id_token)
        if not google_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google OAuth token.",
            )

        email = google_data["email"]
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active Admin account found for this Google email.",
            )

        if google_data.get("picture"):
            user.profile_pic = google_data["picture"]
            self.db.commit()

        raw_refresh_token = generate_secure_token(64)
        refresh_token_hash = hash_token(raw_refresh_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = self.session_repo.create_session(
            user_id=user.id,
            customer_id=None,
            actor_type=user.role.value,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.user_repo.update_last_login(user)

        access_token = create_access_token(
            subject=user.id,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            actor_type=user.role.value,
            email=user.email,
            mobile=user.mobile,
            extra_claims={"session_id": str(session.id)},
        )

        return access_token, raw_refresh_token, user

    # ── CUSTOMER / ENDUSER OTP FLOWS ──────────────────────────────────
    def request_customer_otp(
        self,
        identifier: str,
        purpose: str = "LOGIN",
        visitor_id: uuid.UUID | None = None,
    ) -> tuple[str, str, str, int, str | None]:
        """Generate and dispatch OTP for Customer / Traveler login or registration."""
        cleaned, id_type = self.normalize_identifier(identifier)

        raw_otp = generate_otp(6)
        hashed = hash_otp(raw_otp)

        self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
        self.otp_repo.create_challenge(
            identifier=cleaned,
            identifier_type=id_type,
            otp_hash=hashed,
            purpose=purpose,
            expires_in_seconds=settings.OTP_EXPIRY_SECONDS,
            visitor_id=visitor_id,
        )

        try:
            returned_otp = self._dispatch_otp(cleaned, id_type, raw_otp)
        except HTTPException:
            self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
            raise

        message = f"OTP successfully generated and sent to your {id_type.lower()}."
        return message, cleaned, id_type, settings.OTP_EXPIRY_SECONDS, returned_otp

    def verify_customer_otp(
        self,
        identifier: str,
        otp: str,
        name: str | None = None,
        purpose: str = "LOGIN",
        visitor_id: uuid.UUID | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, Customer]:
        """Verify Customer OTP, find or auto-register Customer, link visitor telemetry,

        and return (access_token, raw_refresh_token, customer).
        """
        cleaned, _ = self.normalize_identifier(identifier)
        challenge = self.otp_repo.get_active_challenge(cleaned, purpose=purpose)

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active OTP challenge found. Please request a new OTP.",
            )

        if challenge.attempts >= challenge.max_attempts:
            self.otp_repo.invalidate_existing(cleaned, purpose=purpose)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum verification attempts exceeded. Please request a new OTP.",
            )

        if not verify_otp(otp, challenge.otp_hash):
            attempts = self.otp_repo.increment_attempts(challenge)
            remaining = challenge.max_attempts - attempts
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
            )

        customer = self.customer_repo.get_by_identifier(cleaned)
        if not customer:
            customer_name = name.strip() if name else "Valued Traveler"
            if challenge.identifier_type == "EMAIL":
                customer = self.customer_repo.create_customer(
                    name=customer_name,
                    email=cleaned,
                    mobile=None,
                    source=LeadSource.WEBSITE,
                )
            else:
                customer = self.customer_repo.create_customer(
                    name=customer_name,
                    mobile=cleaned,
                    email=None,
                    source=LeadSource.WEBSITE,
                )
        elif name and customer.name == "Valued Traveler":
            customer.name = name.strip()
            self.db.commit()

        target_visitor_id = visitor_id or challenge.visitor_id
        if target_visitor_id:
            self.customer_repo.link_visitor_to_customer(
                customer_id=customer.id,
                visitor_id=target_visitor_id,
            )

        self.otp_repo.mark_used(challenge, customer_id=customer.id)

        raw_refresh_token = generate_secure_token(64)
        refresh_token_hash = hash_token(raw_refresh_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = self.session_repo.create_session(
            user_id=None,
            customer_id=customer.id,
            actor_type="CUSTOMER",
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        access_token = create_access_token(
            subject=customer.id,
            role="CUSTOMER",
            actor_type="CUSTOMER",
            email=customer.email,
            mobile=customer.mobile,
            extra_claims={"session_id": str(session.id)},
        )

        return access_token, raw_refresh_token, customer

    # ── CUSTOMER GOOGLE OAUTH FLOW ────────────────────────────────────
    def google_login_customer(
        self,
        id_token: str,
        visitor_id: uuid.UUID | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, Customer]:
        """Authenticate / Register customer via Google OAuth ID token."""
        google_data = verify_google_id_token(id_token)
        if not google_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google OAuth token.",
            )

        email = google_data["email"]
        name = google_data.get("name") or "Valued Traveler"
        picture = google_data.get("picture")

        customer = self.customer_repo.get_by_email(email)
        if not customer:
            customer = self.customer_repo.create_customer(
                name=name,
                email=email,
                mobile=None,
                source=LeadSource.WEBSITE,
            )
            if picture:
                customer.profile_pic = picture
                self.db.commit()
        elif picture:
            customer.profile_pic = picture
            self.db.commit()

        if visitor_id:
            self.customer_repo.link_visitor_to_customer(
                customer_id=customer.id,
                visitor_id=visitor_id,
            )

        raw_refresh_token = generate_secure_token(64)
        refresh_token_hash = hash_token(raw_refresh_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = self.session_repo.create_session(
            user_id=None,
            customer_id=customer.id,
            actor_type="CUSTOMER",
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        access_token = create_access_token(
            subject=customer.id,
            role="CUSTOMER",
            actor_type="CUSTOMER",
            email=customer.email,
            mobile=customer.mobile,
            extra_claims={"session_id": str(session.id)},
        )

        return access_token, raw_refresh_token, customer

    # ── COMMON REFRESH & SESSION ROTATION ──────────────────────────────
    def refresh_session(
        self,
        raw_refresh_token: str | None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Validate refresh token, rotate session preserving absolute 30-day expiration,

        and return (new_access_token, new_raw_refresh_token).
        """
        if not raw_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is missing.",
            )

        token_hash = hash_token(raw_refresh_token)
        session = self.session_repo.get_by_token_hash(token_hash)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        if session.revoked_at is not None:
            self.session_repo.revoke_all_for_actor(
                user_id=session.user_id,
                customer_id=session.customer_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected. All active sessions have been revoked for security.",
            )

        now = datetime.now(timezone.utc)

        expires_at = (
            session.expires_at.replace(tzinfo=timezone.utc)
            if session.expires_at.tzinfo is None
            else session.expires_at
        )
        if now >= expires_at:
            self.session_repo.revoke_session(session)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session has expired (maximum 30-day limit reached).",
            )

        last_used_at = (
            session.last_used_at.replace(tzinfo=timezone.utc)
            if session.last_used_at.tzinfo is None
            else session.last_used_at
        )
        inactivity_limit = last_used_at + timedelta(
            hours=settings.REFRESH_TOKEN_INACTIVITY_HOURS
        )
        if now > inactivity_limit:
            self.session_repo.revoke_session(session)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session expired due to 24 hours of inactivity.",
            )

        if session.actor_type in ("ADMIN", "STAFF") and session.user_id is not None:
            user = self.user_repo.get_by_id(session.user_id)
            if not user or not user.is_active:
                self.session_repo.revoke_session(session)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is deactivated.",
                )
            access_token_subject = user.id
            access_token_role = user.role.value if hasattr(user.role, "value") else str(user.role)
            access_token_actor_type = session.actor_type
            access_token_email = user.email
            access_token_mobile = user.mobile
        else:
            customer = self.customer_repo.get_by_id(session.customer_id)
            if not customer:
                self.session_repo.revoke_session(session)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Customer profile not found.",
                )
            access_token_subject = customer.id
            access_token_role = "CUSTOMER"
            access_token_actor_type = "CUSTOMER"
            access_token_email = customer.email
            access_token_mobile = customer.mobile

        new_raw_refresh_token = generate_secure_token(64)
        new_token_hash = hash_token(new_raw_refresh_token)

        new_session = self.session_repo.rotate_session(
            old_session=session,
            new_token_hash=new_token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        access_token = create_access_token(
            subject=access_token_subject,
            role=access_token_role,
            actor_type=access_token_actor_type,
            email=access_token_email,
            mobile=access_token_mobile,
            extra_claims={"session_id": str(new_session.id)},
        )

        return access_token, new_raw_refresh_token

    def logout(self, raw_refresh_token: str | None) -> None:
        """Revoke the session associated with the provided refresh token."""
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            session = self.session_repo.get_by_token_hash(token_hash)
            if session:
                self.session_repo.revoke_session(session)

    def logout_all_for_actor(
        self,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> int:
        """Revoke all active sessions for the specified user or customer."""
        return self.session_repo.revoke_all_for_actor(
            user_id=user_id,
            customer_id=customer_id,
        )

    def get_actor_sessions(
        self,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        current_refresh_token: str | None = None,
        current_session_id: uuid.UUID | None = None,
    ) -> list[AuthSessionResponse]:
        """Fetch active sessions for actor, marking the current session."""
        sessions = self.session_repo.get_active_sessions_for_actor(
            user_id=user_id,
            customer_id=customer_id,
        )
        current_hash = hash_token(current_refresh_token) if current_refresh_token else None

        result = []
        for s in sessions:
            is_current = (
                (current_session_id is not None and s.id == current_session_id)
                or (current_hash is not None and s.refresh_token_hash == current_hash)
            )
            result.append(
                AuthSessionResponse(
                    id=s.id,
                    actor_type=s.actor_type,
                    user_agent=s.user_agent,
                    ip_address=s.ip_address,
                    created_at=s.created_at,
                    last_used_at=s.last_used_at,
                    expires_at=s.expires_at,
                    is_current=is_current,
                )
            )
        return result

    def revoke_session_by_id(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> None:
        """Revoke a specific session ensuring strict ownership."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found.",
            )

        if user_id and session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found.",
            )
        if customer_id and session.customer_id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found.",
            )

        self.session_repo.revoke_session(session)
