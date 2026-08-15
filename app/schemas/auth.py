from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import LeadSource, UserRole
from app.schemas.customer import CustomerResponse


class OtpRequestSchema(BaseModel):
    identifier: str = Field(
        ...,
        description="Mobile number (e.g. '+919876543210') or Email address",
        min_length=3,
        max_length=255,
    )
    identifier_type: str | None = Field(
        default=None,
        description="MOBILE or EMAIL (auto-detected if omitted)",
    )
    purpose: str = Field(
        default="LOGIN",
        description="LOGIN, VERIFY_MOBILE, or VERIFY_EMAIL",
    )
    visitor_id: UUID | None = Field(
        default=None,
        description="Optional visitor UUID to associate telemetry with this login",
    )


class OtpRequestResponse(BaseModel):
    message: str
    identifier: str
    identifier_type: str
    expires_in: int = Field(default=300, description="OTP validity in seconds")
    dev_otp: str | None = Field(
        default=None,
        description="OTP value returned only in development/test environment for convenience",
    )


class OtpVerifySchema(BaseModel):
    identifier: str = Field(..., description="Mobile number or Email address")
    otp: str = Field(..., min_length=4, max_length=10, description="The 6-digit OTP code")
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Customer name (used if registering a new customer profile)",
    )
    purpose: str = Field(default="LOGIN")
    visitor_id: UUID | None = Field(
        default=None,
        description="Optional anonymous visitor ID to automatically link telemetry",
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


class GoogleAuthSchema(BaseModel):
    id_token: str = Field(..., description="Google ID Token issued by Google Identity Services")
    visitor_id: UUID | None = Field(default=None, description="Optional visitor UUID to link telemetry")


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")
    user: UserResponse


class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")
    customer: CustomerResponse


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiration in seconds (15 minutes)")


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_type: str = "USER"
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool = False


class MessageResponse(BaseModel):
    message: str
