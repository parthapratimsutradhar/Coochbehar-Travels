from enum import StrEnum

    
class UserError(StrEnum):
    USER_NOT_FOUND = "User not found."
    USER_ALREADY_EXISTS = "User already exists."
    
class LeadError(StrEnum):
    LEAD_NOT_FOUND = "Lead not found."
    PACKAGE_NOT_FOUND = "Tour package not found."

class LeadError(StrEnum):
    LEAD_NOT_FOUND = "Lead not found."

class PackageError(StrEnum):
    PACKAGE_NOT_FOUND = "Tour package not found."
