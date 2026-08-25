from enum import StrEnum
from fastapi import status


class UserError(StrEnum):
    USER_NOT_FOUND = "User not found."
    USER_ALREADY_EXISTS = "User already exists."
    EMAIL_ALREADY_EXISTS = "Email is already in use."
    MOBILE_ALREADY_EXISTS = "Mobile is already in use."
    CONTACT_ALREADY_EXISTS = "Account contact messages are already in use."


class LeadError(StrEnum):
    LEAD_NOT_FOUND = "Lead not found."
    PACKAGE_NOT_FOUND = "Tour package not found."


class PackageError(StrEnum):
    PACKAGE_NOT_FOUND = "Tour package not found."


class ReviewError(StrEnum):
    TOUR_NOT_COMPLETED = "You can review only a tour you previously completed or converted."
    ALREADY_REVIEWED = "You have already reviewed this tour."


class AccessError(StrEnum):
    ADMIN_STAFF_REQUIRED = "Admin/Staff access required."
    ADMIN_REQUIRED = "Administrator access required."
    CUSTOMER_REQUIRED = "Customer access required."
    OTP_ADMIN_REQUIRED = "OTP identifier must belong to the authenticated administrator."


class TokenError(StrEnum):
    INVALID_OR_EXPIRED = "Invalid or expired access token."
    SUBJECT_MISSING = "Token subject missing."
    INVALID_USER_ID = "Invalid user ID in token."
    INVALID_CUSTOMER_ID = "Invalid customer ID in token."
    INVALID_ACTOR_ID = "Invalid actor ID in token."
    INVALID_CLAIMS = "Invalid token claims."
    INVALID_ACTOR_TYPE = "Invalid actor type in token."
    USER_INACTIVE = "User inactive or not found."
    CUSTOMER_NOT_FOUND = "Customer not found."


class SystemError(StrEnum):
    VALIDATION_FAILED = "Validation failed"
    UNEXPECTED = "An unexpected error occurred"


class ErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"

    @classmethod
    def from_status_code(cls, status_code: int) -> "ErrorCode | str":
        return {
            status.HTTP_400_BAD_REQUEST: cls.BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED: cls.UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN: cls.FORBIDDEN,
            status.HTTP_404_NOT_FOUND: cls.NOT_FOUND,
            status.HTTP_409_CONFLICT: cls.CONFLICT,
            status.HTTP_429_TOO_MANY_REQUESTS: cls.TOO_MANY_REQUESTS,
            status.HTTP_501_NOT_IMPLEMENTED: cls.NOT_IMPLEMENTED,
            status.HTTP_422_UNPROCESSABLE_CONTENT: cls.VALIDATION_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR: cls.INTERNAL_SERVER_ERROR,
        }.get(status_code, "ERROR")
