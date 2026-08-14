from enum import StrEnum


class InputValidationMessage(StrEnum):
    MOBILE_NUMBER_INVALID = "Mobile number is invalid."
    EMAIL_INVALID = "Email is invalid."
    
class AuthError(StrEnum):
    INVALID_CREDENTIALS = "Invalid email or password."
    ACCESS_DENIED = "Access denied."
    UNAUTHORIZED = "Unauthorized."