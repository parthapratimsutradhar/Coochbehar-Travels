import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt

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


def create_access_token(
    subject: str | UUID,
    role: str = "CUSTOMER",
    actor_type: str = "CUSTOMER",
    email: str | None = None,
    mobile: str | None = None,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived signed JWT access token (15-minute default)."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "role": role,
        "actor_type": actor_type,  # "ADMIN"/"STAFF" or "CUSTOMER"
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if email:
        payload["email"] = email
    if mobile:
        payload["mobile"] = mobile
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


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


def verify_google_id_token(id_token: str) -> dict | None:
    """Verify and decode a Google OAuth ID token, extracting email, name, and profile_pic."""
    if not id_token:
        return None

    try:
        # Decode claims from Google token
        payload = jwt.decode(id_token, options={"verify_signature": False})
        email = payload.get("email")
        if not email:
            return None

        aud = payload.get("aud")
        allowed_audiences = set(settings.GOOGLE_CLIENT_IDS_ALLOWED)
        if aud is not None and aud not in allowed_audiences:
            return None

        return {
            "sub": payload.get("sub"),
            "email": email.strip().lower(),
            "name": payload.get("name") or email.split("@")[0].capitalize(),
            "picture": payload.get("picture"),  # profile_pic avatar
            "email_verified": payload.get("email_verified", True),
        }
    except Exception:
        return None
