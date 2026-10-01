import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
import jwt
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token

from app.core.config import settings


def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure random numeric OTP (e.g. '592817')."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp: str) -> str:
    """Hash an OTP for secure database storage."""
    return hashlib.sha256(otp.strip().encode("utf-8")).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify an entered OTP against its stored SHA-256 hash."""
    if not plain_otp or not hashed_otp:
        return False
    computed_hash = hash_otp(plain_otp)
    return hmac.compare_digest(computed_hash, hashed_otp)


def generate_secure_token(nbytes: int = 64) -> str:
    """Generate a cryptographically secure random URL-safe opaque token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a raw token for server-side persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def compare_token_hashes(hash_a: str, hash_b: str) -> bool:
    """Perform constant-time comparison of two token hashes to prevent timing attacks."""
    return hmac.compare_digest(hash_a, hash_b)


def normalize_role_value(value: object, default: str = "CUSTOMER") -> str:
    """Coerce enum/string role values into the canonical uppercase string used in JWTs."""
    if value is None:
        return default.upper()
    if isinstance(value, str):
        return value.upper()
    if hasattr(value, "value"):
        return str(value.value).upper()
    return str(value).upper()


def create_access_token(
    subject: str | UUID,
    role: str = "CUSTOMER",
    session_id: str | UUID | None = None,
    expires_delta: timedelta | None = None,
    **_: object,
) -> str:
    """Create a lean, canonical JWT access token with only the claims required for auth checks.

    Legacy keyword arguments such as actor_type, email, mobile, and extra_claims are ignored
    to keep the token payload minimal and avoid dead claims.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        "sub": str(subject),
        "role": normalize_role_value(role, default="CUSTOMER"),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if session_id is not None:
        payload["session_id"] = str(session_id)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload dict or None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def verify_google_id_token(
    token: str,
    audience_group: Literal["admin", "customer"],
) -> dict | None:
    """Cryptographically verify a Google ID token against the flow's client IDs."""
    if not token:
        return None

    configured_audiences = getattr(
        settings,
        "GOOGLE_CLIENT_IDS_ADMIN" if audience_group == "admin" else "GOOGLE_CLIENT_IDS_CUSTOMER",
        (),
    ) or ()
    allowed_audiences = set(configured_audiences)
    if not allowed_audiences:
        return None

    try:
        payload = google_id_token.verify_oauth2_token(
            token,
            Request(),
            audience=None,
        )
        email = payload.get("email")
        if not email or payload.get("email_verified") is not True:
            return None

        audience = payload.get("aud")
        token_audiences = {audience} if isinstance(audience, str) else set(audience or ())
        if not allowed_audiences or not token_audiences.intersection(allowed_audiences):
            return None
        if len(token_audiences) > 1 and payload.get("azp") not in allowed_audiences:
            return None

        return {
            "sub": payload.get("sub"),
            "email": email.strip().lower(),
            "name": payload.get("name") or email.split("@")[0].capitalize(),
            "picture": payload.get("picture"),  # profile_pic avatar
            "email_verified": True,
        }
    except Exception:
        return None
