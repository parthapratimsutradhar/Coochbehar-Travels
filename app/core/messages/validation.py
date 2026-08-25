from enum import StrEnum


class InputValidationMessage(StrEnum):
    MOBILE_NUMBER_INVALID = "Mobile number is invalid."
    EMAIL_INVALID = "Email is invalid."


class AuthError(StrEnum):
    INVALID_CREDENTIALS = "Invalid email or password."
    ACCESS_DENIED = "Access denied."
    UNAUTHORIZED = "Unauthorized."
    SMS_NOT_CONFIGURED = "SMS OTP delivery is not configured. Use an email identifier for OTP login."
    ADMIN_NOT_FOUND = "Admin or staff user not found with this identifier."
    OTP_NOT_FOUND = "No active OTP challenge found. Please request a new OTP."
    OTP_ATTEMPTS_EXCEEDED = "Maximum verification attempts exceeded. Please request a new OTP."
    ADMIN_INACTIVE = "Admin user account is inactive or disabled."
    INVALID_GOOGLE_TOKEN = "Invalid Google OAuth token."
    GOOGLE_ADMIN_NOT_FOUND = "No active Admin account found for this Google email."
    INVALID_OTP_PURPOSE = "Customer OTP purpose must be LOGIN or SIGNUP."
    CUSTOMER_ALREADY_EXISTS = "A customer account already exists for this identifier. Please use LOGIN."
    REFRESH_MISSING = "Refresh token is missing."
    REFRESH_INVALID = "Invalid refresh token."
    REFRESH_REUSE = "Refresh token reuse detected. All active sessions have been revoked for security."
    REFRESH_MAX_AGE = "Refresh session has expired (maximum 30-day limit reached)."
    REFRESH_INACTIVE = "Refresh session expired due to 3 days of inactivity."
    ACCOUNT_DEACTIVATED = "User account is deactivated."
    CUSTOMER_NOT_FOUND = "Customer profile not found."