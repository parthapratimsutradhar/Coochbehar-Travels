from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.enums import AdminOtpPurpose, CustomerOtpPurpose, UserRole
from app.core.config import settings


def normalize_referral_code(value):
    if value is None:
        return None

    if isinstance(value, (list, tuple, set)):
        if not value:
            return None
        value = value[0]

    if isinstance(value, str):
        normalized = value.strip()
        return None if normalized == "" else normalized

    return value


# ── Admin Schemas ──────────────────────────────────────────────────────

class AdminOtpRequestSchema(BaseModel):
    """Admin OTP request — identifier and purpose are required."""  

    identifier: str = Field(
        ...,
        description="Mobile number (e.g. '919876543210') or Email address",
        min_length=3,
        max_length=255,
    )
    purpose: AdminOtpPurpose = Field(
        default="LOGIN",
        description="Admin authentication purpose: LOGIN, VERIFY_MOBILE, VERIFY_EMAIL, or DELETE_ACCOUNT",
    )


class AdminOtpVerifySchema(BaseModel):
    """Admin OTP verification — for LOGIN, VERIFY_MOBILE, VERIFY_EMAIL, DELETE_ACCOUNT."""

    identifier: str = Field(
        ...,
        description="Mobile number (e.g. '919876543210') or Email address",
        min_length=3,
        max_length=255,
    )
    otp: str = Field(..., min_length=4, max_length=10, description="The 6-digit OTP code")
    purpose: str = Field(
        default="LOGIN",
        description="LOGIN, VERIFY_MOBILE, VERIFY_EMAIL, or DELETE_ACCOUNT",
    )


class AdminGoogleAuthSchema(BaseModel):
    """Admin Google OAuth — no visitor tracking."""

    id_token: str = Field(..., description="Google ID Token issued by Google Identity Services")


# ── Customer / Enduser Schemas ─────────────────────────────────────────

class CustomerOtpRequestSchema(BaseModel):
    """Customer OTP request — includes visitor_id for telemetry linking."""

    identifier: str = Field(
        ...,
        description="Mobile number (e.g. '919876543210') or Email address",
        min_length=3,
        max_length=255,
    )
    purpose: CustomerOtpPurpose = Field(
        default="LOGIN",
        description="Customer authentication purpose: SIGNUP, LOGIN, VERIFY_MOBILE, VERIFY_EMAIL, or DELETE_ACCOUNT",
    )
    visitor_id: UUID | None = Field(
        default=None,
        description="Optional visitor UUID to associate telemetry with this login",
    )


class CustomerOtpVerifySchema(BaseModel):
    """Customer OTP verification — supports auto-registration and visitor linking."""

    identifier: str = Field(..., description="Mobile number or Email address")
    otp: str = Field(..., min_length=4, max_length=10, description="The 6-digit OTP code")
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Customer name (used if registering a new customer profile)",
    )
    purpose: CustomerOtpPurpose = Field(
        default="LOGIN",
        description="Customer authentication purpose: LOGIN or SIGNUP",
    )
    visitor_id: UUID | None = Field(
        default=None,
        description="Optional anonymous visitor ID to automatically link telemetry",
    )
    referral_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
        description="Referral code provided by the referring customer",
    )

    @field_validator("referral_code", mode="before")
    @classmethod
    def normalize_referral_code(cls, value):
        return normalize_referral_code(value)


class CustomerGoogleAuthSchema(BaseModel):
    """Customer Google OAuth — includes visitor_id for telemetry linking."""

    id_token: str = Field(..., description="Google ID Token issued by Google Identity Services")
    visitor_id: UUID | None = Field(default=None, description="Optional visitor UUID to link telemetry")
    referral_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
        description="Referral code provided by the referring customer",
    )

    @field_validator("referral_code", mode="before")
    @classmethod
    def normalize_referral_code(cls, value):
        return normalize_referral_code(value)


# ── Shared Response Schemas ────────────────────────────────────────────

class OtpRequestResponse(BaseModel):
    identifier: str
    identifier_type: str
    expires_in_sec: int = Field(default=300, description="OTP validity in seconds")
    if settings.IS_DEVELOPMENT:
        dev_otp: str | None = Field(
            default=None,
            description="OTP value returned only in development/test environment for convenience",
        )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_code: str
    name: str
    email: str
    mobile: str
    role: UserRole
    is_active: bool
    profile_pic: str | None = None
    last_login: datetime | None = None
    created_at: datetime


class RefreshSessionRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None,
        description="Optional refresh token in body as fallback for cross-origin environments",
    )


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")
    refresh_token: str | None = Field(
        default=None,
        description="Refresh token for environments where cross-origin 3rd-party cookies are restricted",
    )



class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")
    refresh_token: str | None = Field(
        default=None,
        description="Refresh token for environments where cross-origin 3rd-party cookies are restricted",
    )


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")
    refresh_token: str | None = Field(
        default=None,
        description="Rotated refresh token for environments where cross-origin 3rd-party cookies are restricted",
    )


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_type: str = "ADMIN"
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool = False


class MessageResponse(BaseModel):
    message: str
